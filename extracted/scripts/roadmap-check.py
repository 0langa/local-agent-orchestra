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
}

RESERVED_SUBSYSTEMS = [
    'tools/mcp/',
    'tools/browser/',
    'tools/local_db/',
    'interfaces/web_ui/',
    'interfaces/desktop_ui/',
    'interfaces/api_server/',
    'distributed/',
    'plugins/',
]


# ─── Checkers ────────────────────────────────────────────────────────────────

class ArchitectureChecker:
    """Enforces the 7 Immutable Laws."""

    def __init__(self, root: Path, current_phase: int = 0):
        self.root = root
        self.current_phase = current_phase
        self.core_dir = root / 'core'
        self.violations: List[Violation] = []

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
            content = py_file.read_text()
            for pattern in PROVIDER_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Skip comments and strings
                    line_num = content[:match.start()].count('\n') + 1
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
            content = py_file.read_text()
            for pattern in WORKFLOW_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
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
                tree = ast.parse(py_file.read_text())
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

    def check_law7_policy_engine_for_tools(self):
        """Law 7: All tool calls go through policy engine."""
        # Check for direct subprocess calls outside tools/shell/
        for py_file in self.root.rglob('*.py'):
            if 'tools/shell/' in str(py_file):
                continue  # Shell tool is allowed to use subprocess

            content = py_file.read_text()
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
                    rel_path = py_file.relative_to(self.root)
                    self.violations.append(Violation(
                        level=ViolationLevel.LEVEL_3,
                        rule="Law 7: Safety by Default",
                        file=str(rel_path),
                        line=line_num,
                        message=f"Direct system call '{match.group()}' outside tools/shell/",
                        fix="Route through tools.base.ToolProtocol via policy_engine",
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
                    if result.stdout.strip():
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
        for py_file in self.root.rglob('*.py'):
            content = py_file.read_text()
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

            emoji = {"constitutional": "🔴", "architecture": "🟠",
                     "boundary": "🟡", "style": "🔵"}[level.value]
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
        description="Enforce local-agent-orchestra architecture rules"
    )
    parser.add_argument('--phase', type=int, default=0,
                        help='Current development phase (0-5)')
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
