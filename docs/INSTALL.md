# Installation Guide

## Requirements

- **Python 3.12 or higher**
- **Git**
- **(Optional) Playwright** — only needed for browser automation tool

## Quick Install

```bash
# Clone the repository
git clone https://github.com/0langa/agentheim.git
cd agentheim

# Install in editable mode
pip install -e .
```

## Verify Installation

```bash
# Check CLI is available
python -m ai_team --help

# Run system diagnostics
python -m ai_team doctor
```

## Configure a Provider

Agentheim is provider-agnostic. Copy the example environment file and fill in your provider details:

```bash
cp Agent-Team/.env.example .env
```

Edit `.env` with your provider endpoint and API key:

```env
AI_TEAM_PROVIDER_IDS=default
AI_TEAM_PROVIDER_DEFAULT_TYPE=openai_compatible
AI_TEAM_PROVIDER_DEFAULT_ENDPOINT=https://api.openai.com/v1
AI_TEAM_PROVIDER_DEFAULT_API_KEY_ENV=OPENAI_API_KEY
OPENAI_API_KEY=sk-your-key-here
```

### Supported Provider Types

| Provider | Type | Example Endpoint |
|----------|------|-----------------|
| OpenAI | `openai_compatible` | `https://api.openai.com/v1` |
| Azure OpenAI | `azure_foundry` | `https://your-resource.openai.azure.com/` |
| Ollama (local) | `openai_compatible` | `http://localhost:11434/v1` |
| Grok | `openai_compatible` | Your Grok endpoint |
| AWS Bedrock | `aws_bedrock` | (uses boto3) |
| OCI GenAI | `oci_genai` | (uses OCI SDK) |

### Test Provider Connectivity

```bash
python -m ai_team ping-models
```

## Optional: Install Playwright (for Browser Tool)

If you want to use the browser automation tool:

```bash
pip install playwright
playwright install chromium
```

Without Playwright, the browser tool falls back to HTTP requests.

## Optional: Development Dependencies

For running tests with coverage:

```bash
pip install pytest pytest-cov
```

## Troubleshooting

### `ModuleNotFoundError` on import
Make sure you installed with `-e .` (editable mode) from the repo root.

### Tests fail with `ImportError`
Set `PYTHONPATH` to include the repo root:

```powershell
# Windows
$env:PYTHONPATH="."; pytest tests\ -q

# Linux/Mac
PYTHONPATH="." pytest tests/ -q
```

### `doctor` reports missing provider
Your `.env` file is either missing or the API key environment variable is not set.

### Windows: `pytest` temp cleanup warnings
These are harmless Windows-specific warnings from pytest's temp directory cleanup. They do not affect test results.
