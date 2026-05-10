#!/usr/bin/env python3
"""Bulk rewrite ai_team imports to canonical paths."""
import re
from pathlib import Path

MAPPING = {
    'config.config': 'config.config',
    'core.model_registry': 'core.model_registry',
    'core.errors': 'core.errors',
    'core.json_repair': 'core.json_repair',
    'core.ledger': 'core.ledger',
    'core.patching': 'core.patching',
    'core.policies': 'core.policies',
    'core.repo.command_detect': 'core.repo.command_detect',
    'core.repo.context_pack': 'core.repo.context_pack',
    'core.repo.language_detect': 'core.repo.language_detect',
    'core.repo.redaction': 'core.repo.redaction',
    'core.repo.scanner': 'core.repo.scanner',
    'core.resume': 'core.resume',
    'core.schemas': 'core.schemas',
    'core.state_machine': 'core.state_machine',
    'providers.aws_bedrock': 'providers.aws_bedrock',
    'providers.azure_foundry': 'providers.azure_foundry',
    'providers.base': 'providers.base',
    'providers.oci_genai': 'providers.oci_genai',
    'providers.openai_v1': 'providers.openai_v1',
    'tools.filesystem': 'tools.filesystem',
    'tools.git': 'tools.git',
    'tools.registry': 'tools.registry',
    'tools.shell': 'tools.shell',
    'tools.tests': 'tools.tests',
    'tools.integrations.mcp_client': 'tools.integrations.mcp_client',
    'tools.integrations.web_research': 'tools.integrations.web_research',
    'workflows.coding.agents.base': 'workflows.coding.agents.base',
    'workflows.coding.agents.coder': 'workflows.coding.agents.coder',
    'workflows.coding.agents.orchestrator': 'workflows.coding.agents.orchestrator',
    'workflows.coding.agents.verifier': 'workflows.coding.agents.verifier',
    'workflows.coding.reports.final_report': 'workflows.coding.reports.final_report',
    'workflows.coding.reports.markdown': 'workflows.coding.reports.markdown',
    'workflows.coding.workflows.base': 'workflows.coding.workflows.base',
    'workflows.coding.workflows.coding': 'workflows.coding.workflows.coding',
    'workflows.coding.runtime': 'workflows.coding.runtime',
    'interfaces.cli.cli': 'interfaces.cli.cli',
}


def fix_imports_in_file(path: Path) -> bool:
    original = path.read_text(encoding='utf-8')
    text = original
    for old, new in MAPPING.items():
        old_escaped = old.replace('.', r'\.')
        text = re.sub(rf'from {old_escaped} import', f'from {new} import', text)
        text = re.sub(rf'import {old_escaped}\b', f'import {new}', text)
        text = re.sub(rf'"{old_escaped}', f'"{new}', text)
        text = re.sub(rf"'{old_escaped}", f"'{new}", text)
    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def main() -> None:
    files = list(Path('.').rglob('*.py'))
    fixed = 0
    for f in files:
        rel = str(f).replace('\\', '/')
        if rel.startswith('Agent-Team/') or rel.startswith('extracted/'):
            continue
        if fix_imports_in_file(f):
            fixed += 1
            print(f'Fixed: {rel}')
    print(f'Total files fixed: {fixed}')


if __name__ == '__main__':
    main()
