param(
    [ValidateSet("narrow", "targeted", "broad", "full")]
    [string]$Mode = "targeted",
    [string]$K = ""
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

$baseArgs = @("-q")
if ($K.Trim()) {
    $baseArgs += @("-k", $K.Trim())
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
            "tests/test_federation_transport.py"
        ))
        Invoke-TestSet -Label "broad (memory suite)" -PytestArgs ($baseArgs + @("tests/memory/"))
    }
    "full" {
        Invoke-TestSet -Label "full (entire project test suite)" -PytestArgs $baseArgs
    }
}

Write-Host "Done: mode=$Mode"
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
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run-devtest.ps1") -Mode $Mode -K $K
}
