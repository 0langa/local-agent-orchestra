#!/usr/bin/env python3
"""
Roadmap Architecture Enforcement Script
Validates code changes against the project roadmap and architectural laws.

Usage:
    python scripts/roadmap-check.py              # Check entire repo
    python scripts/roadmap-check.py --pr         # Check PR diff only
    python scripts/roadmap-check.py --phase 0    # Validate phase gate
    python scripts/roadmap-check.py --ci         # CI mode (exit non-zero on violation)

Exit codes:
    0 = All checks passed
    1 = Architectural breach (Level 3+)
    2 = Boundary concern (Level 2)
    3 = File not found / config error
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class ViolationLevel(Enum):
    LEVEL_1 = "style"           # Auto-correct suggestion
    LEVEL_2 = "boundary"        # Requires review
    LEVEL_3 = "architecture"    # Blocks merge
    LEVEL_4 = "constitutional"  # Immediate revert


@dataclass
class Violation:
    level: ViolationLevel
    rule: str
    file: str
    line: Optional[int]
    message: str
    fix: Optional[str] = None


@dataclass
class CheckResult:
    passed: bool
    violations: List[Violation] = field(default_factory=list)


# ─── Configuration ───────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent

# Law 1: These patterns must NOT appear in core/ (except in comments/docs)
PROVIDER_PATTERNS = [
    r'grok', r'openai', r'anthropic', r'ollama', r'lm_studio',
    r'llama_cpp', r'vllm', r'openrouter', r'mistral', r'groq',
    r'azure', r'oci', r'aws', r'google',
]

# Law 1 (continued): Workflow-specific patterns must NOT appear in core/
WORKFLOW_PATTERNS = [
    r'\bcoding\b(?!\s*=)', r'\bresearch\b', r'\bdocument\b',
    r'\bplanner\b', r'\bexecutor\b', r'\bverifier\b',
    r'\borchestrator\b(?!\s*=)',
]

# Law 2: Core must only import from protocol interfaces
CORE_ALLOWED_IMPORTS = {
    'providers.base',
    'tools.base',
    'workflows.base',
    'memory.base',
    'core.',
}

CORE_FORBIDDEN_IMPORTS = {
    'providers.openai',
    'providers.ollama',
    'providers.grok',
    'providers.azure',
    'providers.oci',
    'providers.aws',
    'tools.filesystem',
    'tools.shell',
    'tools.git',
    'tools.http',
    'workflows.coding',
    'workflows.documents',
}

# Phase-locked subsystems
PHASE_LOCK = {
    0: {
        'unlocked': [
            'core/', 'providers/', 'tools/base.py',
            'workflows/base.py', 'workflows/coding/',
            'scripts/', 'config/', 'tests/',
        ],
        'locked': [
            'workflows/documents/',
            'workflows/research/',
            'workflows/file_organization/',
            'workflows/docs_maintenance/',
            'workflows/github_maintenance/',
            'workflows/command_assistant/',
            'memory/vector_retrieval.py',
            'interfaces/guided_tui/',
            'interfaces/web_ui/',
            'interfaces/desktop_ui/',
            'interfaces/api_server/',
            'tools/mcp/',
            'tools/browser/',
            'tools/local_db/',
        ],
    },
    1: {
        'unlocked': ['core/'],
        'locked': ['workflows/', 'interfaces/', 'presets/'],
    },
    2: {
        'unlocked': ['workflows/coding/'],
        'locked': ['presets/', 'interfaces/'],
    },
    3: {
        'unlocked': ['tools/'],
        'locked': ['presets/', 'interfaces/'],
    },
    4: {
        'unlocked': ['presets/', 'interfaces/cli/', 'config/'],
        'locked': ['interfaces/guided_tui/'],
    },
    5: {
        'unlocked': [
            'workflows/documents/',
            'workflows/research/',
            'workflows/file_organization/',
            'workflows/docs_maintenance/',
            'workflows/github_maintenance/',
            'workflows/command_assistant/',
            'interfaces/guided_tui/',
            'memory/',
        ],
        'locked': ['interfaces/web_ui/', 'interfaces/desktop_ui/', 'interfaces/api_server/'],
    },
    6: {
        'unlocked': [
            'interfaces/web_ui/',
            'interfaces/desktop_ui/',
            'interfaces/api_server/',
            'tools/mcp/',
            'tools/browser/',
        ],
        'locked': [],
    },
    7: {
        'unlocked': [
            'core/',
            'providers/',
            'tools/',
            'workflows/',
            'memory/',
            'interfaces/',
            'presets/',
            'config/',
            'tests/',
            'scripts/',
        ],
        'locked': [],
    },
}

PHASE_LOCK_EXEMPTIONS = {
    # V1 release-hotfix: /api/models must be clean-clone safe when no provider
    # profile exists. Keep this narrow so broader API drift still trips Phase 0.
    0: {
        'interfaces/api_server/': {'interfaces/api_server/app.py'},
        # V1 security-hotfix: sanitize run/project paths and error payloads
        # without opening the wider Web UI subsystem for unrelated edits.
        'interfaces/web_ui/': {'interfaces/web_ui/app.py'},
    },
}

RESERVED_SUBSYSTEMS = [
]

# Law 7: Paths allowed to use subprocess/os.system directly
# These are tool implementations that wrap system calls legitimately
SUBPROCESS_EXEMPTIONS = [
    'scripts/roadmap-check.py',              # This checker script
    'scripts/check-agent-instructions.py',   # Instruction linting script
    'scripts/docs_check.py',                 # Release docs gate invokes the local CLI
    'scripts/install_git_hooks.py',          # Developer hook installer invokes git config
    'scripts/package_smoke.py',              # Clean install smoke creates/runs subprocess venvs
    'scripts/refresh_kimi_memory.py',        # Maintainer-only memory refresh invokes git/kimi CLI
    'scripts/live_validate.py',              # Live validation harness shells out by design
    'tools/shell',                           # Shell tool (subprocess is its purpose)
    'tools/git',                             # Git tool (wraps git CLI)
    'core/repo/scanner.py',                  # Repo scanner uses git subprocess for snapshot
    'interfaces/integration_checks.py',      # Diagnostic GitHub auth probe invokes gh status
    'tests/test_adapters.py',                # Adapter tests mock subprocess boundaries
    'tests/test_integration_hardening.py',   # Integration diagnostics tests mock gh subprocess
    'tests/test_packaging.py',               # Packaging tests build wheel/sdist in subprocesses
    'tests/tools/test_git_tool.py',          # GitTool tests create synthetic repos
    'tests/memory/test_stress.py',           # Cross-process stress tests spawn subprocesses
    'interfaces/cli/cli.py',                 # Doctor command checks git availability via subprocess
    'tools/mcp/client.py',                   # MCP client spawns MCP server subprocesses
    'tests/test_import_linting.py',          # Tests the checker itself; needs subprocess
    'tests/test_context_ops_impl.py',        # ContextOps tests spawn git for synthetic repos
    'tests/test_negative_paths.py',          # Negative-path tests spawn git for dirty-repo scenarios
    '.localtest/run-live-ai-smoke.py',       # Local live-test harness (gitignored, not committed)
    # AICtx vendor imports (M1) — imported reference code; subprocess/git calls are
    # legitimate internal AICtx operations and will be mediated through ContextOps
    # or routed through the tool protocol in later milestones.
    'agentheim/vendor/aictx/git/',
    'agentheim/vendor/aictx/io/patches.py',
    'agentheim/vendor/aictx/tests/',
]


# ─── Checkers ────────────────────────────────────────────────────────────────

class ArchitectureChecker:
    """Enforces legacy architecture checks used by roadmap-era validation."""

    def __init__(self, root: Path, current_phase: int = 0):
        self.root = root
        self.current_phase = current_phase
        self.core_dir = root / 'core'
        self.violations: List[Violation] = []
        self._tracked_files = self._load_tracked_files()

    def _load_tracked_files(self) -> Optional[Set[str]]:
        """Return git-tracked files, or None when git metadata is unavailable."""
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                capture_output=True,
                text=True,
                cwd=self.root,
                check=True,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            return None
        return {line.strip().replace('\\', '/') for line in result.stdout.splitlines() if line.strip()}

    def _is_tracked(self, rel_path: str | Path) -> bool:
        if self._tracked_files is None:
            return True
        return str(rel_path).replace('\\', '/') in self._tracked_files

    def check_all(self) -> CheckResult:
        """Run all architecture checks."""
        checks = [
            self.check_law1_no_provider_logic_in_core,
            self.check_law1_no_workflow_logic_in_core,
            self.check_law1_no_concrete_imports_in_core,
            self.check_law7_policy_engine_for_tools,
            self.check_phase_lock,
            self.check_reserved_not_implemented,
            self.check_event_immutability,
            self.check_directory_structure,
            self.check_import_boundaries,
        ]

        for check in checks:
            check()

        passed = not any(
            v.level in (ViolationLevel.LEVEL_3, ViolationLevel.LEVEL_4)
            for v in self.violations
        )
        return CheckResult(passed=passed, violations=self.violations)

    def check_law1_no_provider_logic_in_core(self):
        """Law 1: No provider-specific logic in core/."""
        if not self.core_dir.exists():
            return

        for py_file in self.core_dir.rglob('*.py'):
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            ignored_lines = self._ignored_literal_lines(content)
            for pattern in PROVIDER_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Skip comments and strings
                    line_num = content[:match.start()].count('\n') + 1
                    if line_num in ignored_lines:
                        continue
                    line = content.split('\n')[line_num - 1].strip()
                    if line.startswith('#') or line.startswith('"""') or line.startswith("'''"):
                        continue

                    rel_path = py_file.relative_to(self.root)
                    self.violations.append(Violation(
                        level=ViolationLevel.LEVEL_3,
                        rule="Law 1: Core Ignorance",
                        file=str(rel_path),
                        line=line_num,
                        message=f"Provider pattern '{pattern}' found in core: {line}",
                        fix=f"Move provider-specific logic to providers/ directory",
                    ))

    def check_law1_no_workflow_logic_in_core(self):
        """Law 1: No workflow-specific logic in core/."""
        if not self.core_dir.exists():
            return

        for py_file in self.core_dir.rglob('*.py'):
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            ignored_lines = self._ignored_literal_lines(content)
            for pattern in WORKFLOW_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    if line_num in ignored_lines:
                        continue
                    line = content.split('\n')[line_num - 1].strip()
                    if line.startswith('#') or '"' in line or "'" in line:
                        continue

                    rel_path = py_file.relative_to(self.root)
                    self.violations.append(Violation(
                        level=ViolationLevel.LEVEL_3,
                        rule="Law 1: Core Ignorance",
                        file=str(rel_path),
                        line=line_num,
                        message=f"Workflow pattern '{pattern}' found in core: {line}",
                        fix=f"Move workflow-specific logic to workflows/ directory",
                    ))

    def check_law1_no_concrete_imports_in_core(self):
        """Check that core only imports from protocol interfaces."""
        if not self.core_dir.exists():
            return

        for py_file in self.core_dir.rglob('*.py'):
            try:
                tree = ast.parse(py_file.read_text(encoding='utf-8'))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        for forbidden in CORE_FORBIDDEN_IMPORTS:
                            if node.module.startswith(forbidden):
                                rel_path = py_file.relative_to(self.root)
                                self.violations.append(Violation(
                                    level=ViolationLevel.LEVEL_3,
                                    rule="Law 1: Core Ignorance",
                                    file=str(rel_path),
                                    line=node.lineno,
                                    message=f"Forbidden import from '{node.module}' in core/",
                                    fix=f"Import from {'.'.join(node.module.split('.')[:2])}.base instead",
                                ))

    def _is_subprocess_exempt(self, file_path: str) -> bool:
        """Check if a file is exempt from subprocess restrictions."""
        normalized = file_path.replace("\\", "/")
        for exempt in SUBPROCESS_EXEMPTIONS:
            if exempt in normalized:
                return True
        return False

    def check_law7_policy_engine_for_tools(self):
        """Law 7: All tool calls go through policy engine."""
        # Paths to skip entirely (e.g. gitignored reference repos)
        EXCLUDED_DIRS = {'AICtx', '.git', '.venv', '.local-maintainer', '.localtest', '__pycache__'}
        for py_file in self.root.rglob('*.py'):
            file_path = str(py_file)
            rel_path = str(py_file.relative_to(self.root))
            if not self._is_tracked(rel_path):
                continue

            # Skip excluded directories
            parts = Path(rel_path).parts
            if any(p in EXCLUDED_DIRS for p in parts):
                continue
            # Skip third-party dependencies and cache directories
            if '/.venv/' in file_path.replace('\\', '/') or '\\.venv\\' in file_path:
                continue
            if '__pycache__' in file_path or 'node_modules' in file_path:
                continue

            # Skip exempt paths (shell tool, git tool, self, legacy locations)
            if self._is_subprocess_exempt(file_path) or self._is_subprocess_exempt(rel_path):
                continue

            content = py_file.read_text(encoding='utf-8')
            direct_patterns = [
                r'subprocess\.(run|call|Popen)',
                r'os\.system\(',
                r'os\.remove\(',
                r'os\.rmdir\(',
                r'shutil\.rmtree\(',
            ]
            for pattern in direct_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    self.violations.append(Violation(
                        level=ViolationLevel.LEVEL_3,
                        rule="Law 7: Safety by Default",
                        file=rel_path,
                        line=line_num,
                        message=f"Direct system call '{match.group()}' outside tools/shell/ or tools/git/",
                        fix="Route through tools.base.ToolProtocol via policy_engine, or add to SUBPROCESS_EXEMPTIONS if legitimate",
                    ))

    def check_phase_lock(self):
        """Check that only unlocked subsystems are modified."""
        if self.current_phase not in PHASE_LOCK:
            return

        lock_config = PHASE_LOCK[self.current_phase]
        unlocked = lock_config['unlocked']
        locked = lock_config['locked']

        for locked_path in locked:
            full_path = self.root / locked_path
            if full_path.exists():
                # Check if files have been modified (using git if available)
                try:
                    result = subprocess.run(
                        ['git', 'diff', '--name-only', 'HEAD', '--', str(full_path)],
                        capture_output=True, text=True, cwd=self.root
                    )
                    modified = {
                        line.strip().replace('\\', '/')
                        for line in result.stdout.splitlines()
                        if line.strip()
                    }
                    exempt = PHASE_LOCK_EXEMPTIONS.get(self.current_phase, {}).get(locked_path, set())
                    modified -= exempt
                    if modified:
                        self.violations.append(Violation(
                            level=ViolationLevel.LEVEL_2,
                            rule="Phase Lock",
                            file=locked_path,
                            line=None,
                            message=f"Locked subsystem '{locked_path}' has modifications in Phase {self.current_phase}",
                            fix=f"Defer to Phase {self.current_phase + 1}+ or get Architecture Lead approval",
                        ))
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass

    def check_reserved_not_implemented(self):
        """Check that reserved Phase 6 systems are not implemented."""
        for reserved in RESERVED_SUBSYSTEMS:
            full_path = self.root / reserved
            if full_path.exists():
                files = list(full_path.rglob('*')) if full_path.is_dir() else [full_path]
                code_files = [f for f in files if f.suffix == '.py']
                if code_files:
                    self.violations.append(Violation(
                        level=ViolationLevel.LEVEL_4,
                        rule="Phase 6 Reserved Architecture",
                        file=reserved,
                        line=None,
                        message=f"Reserved subsystem '{reserved}' has implementation files",
                        fix="Remove implementation or get explicit Architecture Lead approval for early unlock",
                    ))

    def check_event_immutability(self):
        """Check that ledger events are not modified after creation."""
        EXCLUDED_DIRS = {'AICtx', '.git', '.venv', '.local-maintainer', '.localtest', '__pycache__'}
        for py_file in self.root.rglob('*.py'):
            file_path = str(py_file)
            rel_path = str(py_file.relative_to(self.root))
            if not self._is_tracked(rel_path):
                continue
            # Skip excluded directories
            parts = Path(rel_path).parts
            if any(p in EXCLUDED_DIRS for p in parts):
                continue
            # Skip third-party dependencies and cache directories
            if '/.venv/' in file_path.replace('\\', '/') or '\\.venv\\' in file_path:
                continue
            if '__pycache__' in file_path or 'node_modules' in file_path:
                continue
            content = py_file.read_text(encoding='utf-8')
            # Look for patterns that suggest event modification
            mutation_patterns = [
                r'ledger\[.*\]\s*=',
                r'event\[.*\]\s*=',
                r'\.events\[.*\]\s*=',
            ]
            for pattern in mutation_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    rel_path = py_file.relative_to(self.root)
                    self.violations.append(Violation(
                        level=ViolationLevel.LEVEL_4,
                        rule="Law 5: Event-Sourced Truth",
                        file=str(rel_path),
                        line=line_num,
                        message=f"Potential event mutation: {match.group()}",
                        fix="Events are append-only. Create new event, don't modify existing.",
                    ))

    def check_directory_structure(self):
        """Check canonical directory structure exists."""
        required_dirs = [
            'core/', 'providers/', 'tools/', 'workflows/',
            'memory/', 'interfaces/cli/', 'presets/', 'config/',
            'tests/', 'docs/', 'scripts/',
        ]
        for dir_path in required_dirs:
            full_path = self.root / dir_path
            if not full_path.exists():
                self.violations.append(Violation(
                    level=ViolationLevel.LEVEL_3,
                    rule="Canonical Structure",
                    file=dir_path,
                    line=None,
                    message=f"Required directory '{dir_path}' does not exist",
                    fix=f"Create directory: mkdir -p {dir_path}",
                ))

    def check_import_boundaries(self):
        """Phase 7: Interfaces MUST import only from core.public_api."""
        interfaces_dir = self.root / 'interfaces'
        if not interfaces_dir.exists():
            return

        for py_file in interfaces_dir.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    # Only check imports from core.*
                    if not node.module.startswith('core.'):
                        continue
                    # Allow core.public_api
                    if node.module == 'core.public_api' or node.module.startswith('core.public_api.'):
                        continue
                    rel_path = py_file.relative_to(self.root)
                    self.violations.append(Violation(
                        level=ViolationLevel.LEVEL_3,
                        rule="Phase 7: Public API Boundary",
                        file=str(rel_path),
                        line=node.lineno,
                        message=f"Interface imports from '{node.module}'; must use 'core.public_api'",
                        fix="Replace with 'from core.public_api import ...'",
                    ))

        workflow_paths = [
            self.root / 'workflows',
        ]
        allowed_workflow_exceptions = {
            'workflows/base.py',
        }
        for base_dir in workflow_paths:
            if not base_dir.exists():
                continue
            for py_file in base_dir.rglob('*.py'):
                rel_path = str(py_file.relative_to(self.root)).replace('\\', '/')
                if rel_path in allowed_workflow_exceptions:
                    continue
                if '/agents/' in rel_path:
                    continue
                try:
                    content = py_file.read_text(encoding='utf-8', errors='ignore')
                    tree = ast.parse(content)
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if not node.module.startswith('core.'):
                            continue
                        if node.module == 'core.public_api' or node.module.startswith('core.public_api.'):
                            continue
                        self.violations.append(Violation(
                            level=ViolationLevel.LEVEL_3,
                            rule="Phase 7: Workflow Public API Boundary",
                            file=rel_path,
                            line=node.lineno,
                            message=f"Workflow imports from '{node.module}'; use 'core.public_api' in workflow-facing code",
                            fix="Replace with 'from core.public_api import ...' or move internal-only code behind the public facade",
                        ))

    def _ignored_literal_lines(self, content: str) -> set[int]:
        """Return 1-based line numbers occupied by docstrings or bare string literals."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return set()

        ignored: set[int] = set()
        for node in ast.walk(tree):
            value = None
            if isinstance(node, ast.Expr):
                value = node.value
            elif isinstance(node, ast.Constant):
                value = node
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                start = getattr(value, "lineno", None)
                end = getattr(value, "end_lineno", start)
                if start is None:
                    continue
                for line_no in range(start, (end or start) + 1):
                    ignored.add(line_no)
        return ignored


# ─── Reporter ────────────────────────────────────────────────────────────────

class ViolationReporter:
    """Reports violations in human and machine-readable formats."""

    @staticmethod
    def console_report(result: CheckResult) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("ROADMAP ARCHITECTURE CHECK")
        lines.append("=" * 70)

        by_level = {}
        for v in result.violations:
            by_level.setdefault(v.level, []).append(v)

        for level in (ViolationLevel.LEVEL_4, ViolationLevel.LEVEL_3,
                      ViolationLevel.LEVEL_2, ViolationLevel.LEVEL_1):
            if level not in by_level:
                continue

            emoji = {"constitutional": "[L4]", "architecture": "[L3]",
                     "boundary": "[L2]", "style": "[L1]"}[level.value]
            lines.append(f"\n{emoji} {level.name} ({level.value.upper()}) — {len(by_level[level])} violation(s)")
            lines.append("-" * 50)

            for v in by_level[level]:
                loc = f"{v.file}:{v.line}" if v.line else v.file
                lines.append(f"  [{v.rule}]")
                lines.append(f"  Location: {loc}")
                lines.append(f"  Issue: {v.message}")
                if v.fix:
                    lines.append(f"  Fix: {v.fix}")
                lines.append("")

        lines.append("=" * 70)
        total = len(result.violations)
        critical = len(by_level.get(ViolationLevel.LEVEL_4, []))
        breaches = len(by_level.get(ViolationLevel.LEVEL_3, []))

        if critical > 0:
            lines.append(f"RESULT: FAILED — {critical} constitutional violation(s), {breaches} architectural breach(es)")
            lines.append("Action: Immediate revert required")
        elif breaches > 0:
            lines.append(f"RESULT: FAILED — {breaches} architectural breach(es)")
            lines.append("Action: Blocks merge until resolved")
        elif total > 0:
            lines.append(f"RESULT: WARNING — {total} concern(s) requiring review")
        else:
            lines.append("RESULT: PASSED — All checks clear")

        return "\n".join(lines)

    @staticmethod
    def json_report(result: CheckResult) -> str:
        data = {
            "passed": result.passed,
            "total_violations": len(result.violations),
            "violations": [
                {
                    "level": v.level.name,
                    "rule": v.rule,
                    "file": v.file,
                    "line": v.line,
                    "message": v.message,
                    "fix": v.fix,
                }
                for v in result.violations
            ],
        }
        return json.dumps(data, indent=2)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Enforce agentheim architecture rules"
    )
    parser.add_argument('--phase', type=int, default=0,
                        help='Current development phase (0-7)')
    parser.add_argument('--pr', action='store_true',
                        help='Check PR diff only')
    parser.add_argument('--ci', action='store_true',
                        help='CI mode (exit non-zero on violation)')
    parser.add_argument('--json', action='store_true',
                        help='Output JSON instead of console')
    parser.add_argument('--root', type=Path, default=PROJECT_ROOT,
                        help='Project root directory')

    args = parser.parse_args()

    if not args.root.exists():
        print(f"Error: Project root not found: {args.root}", file=sys.stderr)
        sys.exit(3)

    checker = ArchitectureChecker(args.root, current_phase=args.phase)
    result = checker.check_all()

    if args.json:
        print(ViolationReporter.json_report(result))
    else:
        print(ViolationReporter.console_report(result))

    if args.ci:
        if any(v.level == ViolationLevel.LEVEL_4 for v in result.violations):
            sys.exit(1)
        elif any(v.level == ViolationLevel.LEVEL_3 for v in result.violations):
            sys.exit(1)
        elif any(v.level == ViolationLevel.LEVEL_2 for v in result.violations):
            sys.exit(2)

    sys.exit(0 if result.passed else 1)


if __name__ == '__main__':
    main()
