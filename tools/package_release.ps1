param(
    [switch]$SkipValidation
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$distRoot = Join-Path $repoRoot 'dist'
$releaseRoot = Join-Path $repoRoot 'release'
$specPath = Join-Path $repoRoot 'NewMusicBuilder.spec'
$appDistRoot = Join-Path $distRoot 'NewMusicBuilder'
$workspaceRoot = Join-Path $repoRoot 'workspace'
$logsRoot = Join-Path $repoRoot 'logs'
$diagnosticsRoot = Join-Path $workspaceRoot 'diagnostics'

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Action,
        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Reset-RuntimeState {
    $workspacePath = [System.IO.Path]::GetFullPath($workspaceRoot)
    $logsPath = [System.IO.Path]::GetFullPath($logsRoot)
    $diagnosticsPath = [System.IO.Path]::GetFullPath($diagnosticsRoot)

    New-Item -ItemType Directory -Path $workspacePath -Force | Out-Null
    New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
    New-Item -ItemType Directory -Path $diagnosticsPath -Force | Out-Null

    Get-ChildItem -Path $diagnosticsPath -Force -ErrorAction SilentlyContinue | Remove-Item -Force

    Set-Content -Path (Join-Path $logsPath 'new_music_builder.log') -Value '' -NoNewline
    Set-Content -Path (Join-Path $logsPath 'startup_fatal.log') -Value '' -NoNewline
    Set-Content -Path (Join-Path $logsPath 'runtime_fatal.log') -Value '' -NoNewline

    $runtimeReset = @'
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path("src").resolve()))

from new_music_builder.domain.models import ProjectConfig
from new_music_builder.services.recent_projects import RecentProjectsStore
from new_music_builder.services.session_store import SessionStore

workspace = Path("workspace")
workspace.mkdir(parents=True, exist_ok=True)

store = SessionStore(workspace / "last_session.json")
store.last_automatic_textures_enabled = True
store.last_text_tooltips_enabled = True
store.save(ProjectConfig(), "")

recent = RecentProjectsStore(workspace / "recent.json")
recent.file_path.write_text(json.dumps({"recent": []}, indent=2), encoding="utf-8")
'@

    Invoke-Step -Action { $runtimeReset | python - } -FailureMessage 'Runtime state reset failed.'
}

Push-Location $repoRoot
try {
    $version = python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('src').resolve())); import new_music_builder; print(new_music_builder.__version__)"
    if (-not $version) {
        throw 'Unable to resolve app version.'
    }
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to resolve app version.'
    }

    Invoke-Step -Action { python -m PyInstaller --version | Out-Null } -FailureMessage 'PyInstaller is not available.'

    if (-not $SkipValidation) {
        Invoke-Step -Action { python -m compileall src } -FailureMessage 'compileall validation failed.'
        Invoke-Step -Action { pytest -q } -FailureMessage 'pytest validation failed.'
    }

    Reset-RuntimeState

    if (Test-Path $appDistRoot) {
        Remove-Item -LiteralPath $appDistRoot -Recurse -Force
    }

    New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
    Invoke-Step -Action { python -m PyInstaller --clean --noconfirm $specPath } -FailureMessage 'PyInstaller build failed.'

    if (-not (Test-Path $appDistRoot)) {
        throw "Expected packaged app folder was not created: $appDistRoot"
    }

    $zipPath = Join-Path $releaseRoot "NewMusicBuilder-v$version-win64.zip"
    if (Test-Path $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Compress-Archive -Path $appDistRoot -DestinationPath $zipPath -CompressionLevel Optimal

    Write-Host "Windows release package created: $zipPath"
}
finally {
    Pop-Location
}
