param(
    [ValidateSet("narrow", "targeted", "broad", "full", "directive", "baseline", "phase7", "auto")]
    [string]$Mode = "auto",
    [string]$K = "",
    [switch]$NoPrompt
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-TestSet {
    param(
        [string]$Label,
        [string[]]$PytestArgs,
        [string]$WorkingDir = $RepoRoot
    )
    Write-Host "==> $Label"
    Write-Host "pytest $($PytestArgs -join ' ')"
    Push-Location $WorkingDir
    try {
        & pytest @PytestArgs
        if ($LASTEXITCODE -ne 0) {
            throw "pytest failed in '$Label' with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-CommandCheck {
    param(
        [string]$Label,
        [string[]]$Command,
        [string]$WorkingDir = $RepoRoot
    )
    Write-Host "==> $Label"
    Write-Host ($Command -join " ")
    Push-Location $WorkingDir
    try {
        & $Command[0] $Command[1..($Command.Length - 1)]
        if ($LASTEXITCODE -ne 0) {
            throw "'$Label' failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

$baseArgs = @("-q")
if ($K.Trim()) {
    $baseArgs += @("-k", $K.Trim())
}

function Resolve-AutoMode {
    param([string]$RepoRoot)
    Push-Location $RepoRoot
    try {
        $null = & git rev-parse --git-dir 2>$null
        if ($LASTEXITCODE -ne 0) {
            return "targeted"
        }
        $changed = (& git diff --name-only) + (& git diff --cached --name-only) | Select-Object -Unique
        if (-not $changed) {
            return "targeted"
        }
        $broadDirs = @("core/", "workflows/", "memory/", "federation/", "marketplace/", "monitoring/", "multimodal/")
        $targetedDirs = @("tools/", "interfaces/", "config/", "providers/", "tests/", "presets/")
        $directiveDirs = @("docs/", "scripts/", ".github/", "devtest/")
        $hasBroad = $false
        $hasTargeted = $false
        $hasDirective = $false
        foreach ($file in $changed) {
            foreach ($d in $broadDirs) {
                if ($file.StartsWith($d)) { $hasBroad = $true }
            }
            foreach ($d in $targetedDirs) {
                if ($file.StartsWith($d)) { $hasTargeted = $true }
            }
            foreach ($d in $directiveDirs) {
                if ($file.StartsWith($d)) { $hasDirective = $true }
            }
        }
        if ($hasBroad) { return "broad" }
        if ($hasTargeted) { return "targeted" }
        if ($hasDirective) { return "directive" }
        return "targeted"
    }
    finally {
        Pop-Location
    }
}

if ($Mode -eq "auto") {
    $Mode = Resolve-AutoMode -RepoRoot $RepoRoot
    Write-Host "Auto-selected mode: $Mode"
}

switch ($Mode) {
    "narrow" {
        Invoke-TestSet -Label "narrow (critical core + cli + preset smoke)" -PytestArgs ($baseArgs + @(
            "tests/core/test_model_registry.py",
            "tests/smoke/test_cli.py",
            "tests/smoke/test_presets.py"
        ))
    }
    "targeted" {
        Invoke-TestSet -Label "targeted (core + smoke + mcp + tools)" -PytestArgs ($baseArgs + @(
            "tests/core/test_model_registry.py",
            "tests/core/test_schemas.py",
            "tests/core/test_ledger.py",
            "tests/smoke/test_cli.py",
            "tests/smoke/test_presets.py",
            "tests/test_mcp.py",
            "tests/test_local_db_tool.py"
        ))
    }
    "broad" {
        Invoke-TestSet -Label "broad (high-signal functional set)" -PytestArgs ($baseArgs + @(
            "tests/core/test_model_registry.py",
            "tests/core/test_schemas.py",
            "tests/core/test_ledger.py",
            "tests/core/test_errors.py",
            "tests/core/test_redaction.py",
            "tests/smoke/test_cli.py",
            "tests/smoke/test_presets.py",
            "tests/smoke/test_workflows.py",
            "tests/smoke/test_workflow_execution.py",
            "tests/test_mcp.py",
            "tests/test_mcp_pool.py",
            "tests/test_local_db_tool.py",
            "tests/test_browser_tool.py",
            "tests/test_distributed.py",
            "tests/test_distributed_transport.py",
            "tests/test_web_ui.py",
            "tests/test_api_server.py",
            "tests/test_run_executor.py",
            "tests/test_tool_protocol.py",
            "tests/test_federation_transport.py",
            "tests/test_events.py",
            "tests/test_ledger_hash.py",
            "tests/test_ledger_index.py",
            "tests/test_ledger_checkpoints.py",
            "tests/test_error_classification.py",
            "tests/test_retry_engine.py",
            "tests/test_step_budget.py",
            "tests/test_workflow_runner.py",
            "tests/test_workflow_runner_parallel.py",
            "tests/test_artifact_store.py",
            "tests/test_context_packer.py",
            "tests/test_agent_protocol.py",
            "tests/test_public_api.py",
            "tests/test_workflow_isolation.py",
            "tests/test_policy_engine.py",
            "tests/test_privacy_enforcer.py",
            "tests/test_approval_workflow.py",
            "tests/test_policy_audit.py",
            "tests/test_cascading_router.py",
            "tests/test_resume.py",
            "tests/test_replay_engine.py"
        ))
        Invoke-TestSet -Label "broad (memory suite)" -PytestArgs ($baseArgs + @("tests/memory/"))
    }
    "full" {
        Invoke-TestSet -Label "full (entire project test suite)" -PytestArgs $baseArgs
    }
    "directive" {
        Invoke-CommandCheck -Label "directive governance lint" -Command @("python", "scripts/check-agent-instructions.py")
        Invoke-CommandCheck -Label "repo-local cli help smoke" -Command @("python", "-m", "interfaces.cli.cli", "--help")
        Invoke-CommandCheck -Label "repo-local doctor smoke" -Command @("python", "-m", "interfaces.cli.cli", "doctor", "--skip-connectivity")
    }
    "baseline" {
        Invoke-CommandCheck -Label "baseline governance lint" -Command @("python", "scripts/check-agent-instructions.py")
        Invoke-CommandCheck -Label "baseline cli help smoke" -Command @("python", "-m", "interfaces.cli.cli", "--help")
        Invoke-CommandCheck -Label "baseline doctor smoke" -Command @("python", "-m", "interfaces.cli.cli", "doctor", "--skip-connectivity")
        Invoke-CommandCheck -Label "baseline provider template load" -Command @("python", "-m", "interfaces.cli.cli", "provider", "templates")
        Invoke-CommandCheck -Label "baseline preset registry load" -Command @("python", "-c", "from presets import PRESET_REGISTRY; ids=[p.preset_id for p in PRESET_REGISTRY.list()]; assert ids; print('presets:', ','.join(ids))")
        Invoke-CommandCheck -Label "baseline tool registry load" -Command @("python", "-c", "from tools.registry import ToolRegistry; tools=[t.tool_id for t in ToolRegistry('.').tool_objects()]; assert {'filesystem','git','shell.execute','browser','local_db','http.request','memory'} <= set(tools); print('tools:', ','.join(sorted(tools)))")
        Invoke-CommandCheck -Label "baseline pytest collection" -Command @("pytest", "--collect-only", "-q")
    }
    "phase7" {
        Write-Host "WARNING: phase7 mode is legacy. Prefer -Mode directive plus targeted/broad tests for new directive-system work."
        Invoke-TestSet -Label "phase7 (production hardening - all new tests)" -PytestArgs ($baseArgs + @(
            "tests/test_events.py",
            "tests/test_ledger_hash.py",
            "tests/test_ledger_index.py",
            "tests/test_ledger_checkpoints.py",
            "tests/test_error_classification.py",
            "tests/test_retry_engine.py",
            "tests/test_step_budget.py",
            "tests/test_workflow_runner.py",
            "tests/test_workflow_runner_parallel.py",
            "tests/test_artifact_store.py",
            "tests/test_context_packer.py",
            "tests/test_agent_protocol.py",
            "tests/test_public_api.py",
            "tests/test_provider_lazy_loading.py",
            "tests/test_interface_isolation.py",
            "tests/test_workflow_isolation.py",
            "tests/test_import_linting.py",
            "tests/test_approval_workflow.py",
            "tests/test_policy_audit.py",
            "tests/test_privacy_enforcer.py",
            "tests/test_policy_engine.py",
            "tests/test_cascading_router.py",
            "tests/test_resume.py",
            "tests/test_replay_engine.py"
        ))
    }
}

Write-Host "Done: mode=$Mode"
if ($Mode -eq "phase7") {
    Write-Host "==> legacy phase7 architecture gate"
    Push-Location $RepoRoot
    try {
        & python scripts/roadmap-check.py --phase 7 --ci
        if ($LASTEXITCODE -ne 0) {
            throw "roadmap-check failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}
Write-Host ""
Write-Host "Optional post-run actions:"
Write-Host "1) Clear pytest temp artifacts"
Write-Host "2) Clear local pytest cache"
Write-Host "3) Re-run same suite"
Write-Host ""
Write-Host "Prompt format: [Y]es / [N]o / [A]ll"

$runAll = $false

function Ask-YNA {
    param([string]$Question)
    if ($NoPrompt) { return "N" }
    if ($runAll) { return "Y" }
    $reply = Read-Host "$Question [Y/N/A]"
    if (-not $reply) { return "N" }
    $value = $reply.Trim().ToUpperInvariant()
    if ($value -eq "A") {
        $script:runAll = $true
        return "Y"
    }
    if ($value -eq "Y" -or $value -eq "N") { return $value }
    return "N"
}

if ((Ask-YNA "Run action 1 now?") -eq "Y") {
    Remove-Item -LiteralPath "$env:TEMP\pytest-of-$env:USERNAME" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Action 1 done."
}

if ((Ask-YNA "Run action 2 now?") -eq "Y") {
    Remove-Item -LiteralPath (Join-Path $RepoRoot ".pytest_cache") -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Action 2 done."
}

if ((Ask-YNA "Run action 3 now?") -eq "Y") {
    Write-Host "Re-running mode=$Mode"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run-devtest.ps1") -Mode $Mode -K $K -NoPrompt:$NoPrompt
}
