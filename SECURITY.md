# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| Latest `master` | Yes |
| Latest tagged release | Yes |
| Older commits/releases | No |

Agentheim is developed as an open-source local-first product. Security fixes are applied to the current `master` branch and the latest tagged release.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately through GitHub Security Advisories for this repository:

https://github.com/0langa/agentheim/security/advisories/new

Do not open a public issue for suspected vulnerabilities. Include:

- The affected component.
- Steps to reproduce.
- Expected impact.
- Relevant logs with secrets redacted.

## Handling

Maintainers will acknowledge valid reports, investigate impact, and publish fixes through normal release notes once remediation is available.

## Security Features

- Path confinement for workspace and run-artifact operations.
- Policy evaluation for tool invocations.
- Secret redaction for logs, API responses, and artifacts.
- Local-first defaults; provider calls require explicit user configuration.
- Approval gates for higher-risk operations.
- Append-only run ledger for auditability.
