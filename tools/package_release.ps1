param(
    [switch]$SkipValidation
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$distRoot = Join-Path $repoRoot 'dist'
$releaseRoot = Join-Path $repoRoot 'release'
$specPath = Join-Path $repoRoot 'NewMusicBuilder.spec'
$appDistRoot = Join-Path $distRoot 'NewMusicBuilder'
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

function Initialize-PackagedRuntimeState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetRoot
    )

    $targetPath = [System.IO.Path]::GetFullPath($TargetRoot)
    $workspacePath = Join-Path $targetPath 'workspace'
    $logsPath = Join-Path $targetPath 'logs'
    $generatedTexturesPath = Join-Path $targetPath 'Generated Textures'
    $diagnosticsPath = Join-Path $workspacePath 'diagnostics'

    New-Item -ItemType Directory -Path $workspacePath -Force | Out-Null
    New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
    New-Item -ItemType Directory -Path $generatedTexturesPath -Force | Out-Null
    New-Item -ItemType Directory -Path $diagnosticsPath -Force | Out-Null

    Set-Content -Path (Join-Path $logsPath 'new_music_builder.log') -Value '' -NoNewline
    Set-Content -Path (Join-Path $logsPath 'startup_fatal.log') -Value '' -NoNewline
    Set-Content -Path (Join-Path $logsPath 'runtime_fatal.log') -Value '' -NoNewline

    $runtimeSeed = @'
from pathlib import Path
import json
import sys

target_root = Path(sys.argv[1]).resolve()
workspace = target_root / "workspace"
workspace.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(Path("src").resolve()))

from new_music_builder.domain.models import ProjectConfig
from new_music_builder.services.recent_projects import RecentProjectsStore
from new_music_builder.services.session_store import SessionStore

project = ProjectConfig()
project.ensure_defaults()
project.ogg_output_folder = ""
project.workshop_output_folder = ""
project.legacy_mode_enabled = False

store = SessionStore(workspace / "last_session.json")
store.last_ogg_output_folder = ""
store.last_automatic_textures_enabled = True
store.last_legacy_mode_enabled = False
store.last_regenerate_textures_on_project_load_enabled = False
store.last_text_tooltips_enabled = True
store.save(project, "")

recent = RecentProjectsStore(workspace / "recent.json")
recent.file_path.write_text(json.dumps({"recent": []}, indent=2), encoding="utf-8")
'@

    Invoke-Step -Action { $runtimeSeed | python - $targetPath } -FailureMessage 'Packaged runtime seed failed.'
}

function Prune-WindowsReleaseArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetRoot
    )

    $targetPath = [System.IO.Path]::GetFullPath($TargetRoot)
    $tkdndRoot = Join-Path $targetPath '_internal\tkinterdnd2\tkdnd'
    if (-not (Test-Path $tkdndRoot)) {
        return
    }

    $keepFolder = Join-Path $tkdndRoot 'win-x64'
    if (-not (Test-Path $keepFolder)) {
        throw "Expected tkinterdnd2 win-x64 runtime folder was not found: $keepFolder"
    }

    Get-ChildItem -Path $tkdndRoot -Directory | Where-Object { $_.Name -ne 'win-x64' } | Remove-Item -Recurse -Force

    $keepFiles = @(
        'pkgIndex.tcl',
        'tkdnd.tcl',
        'tkdnd_compat.tcl',
        'tkdnd_generic.tcl',
        'tkdnd_utils.tcl',
        'tkdnd_windows.tcl'
    )

    Get-ChildItem -Path $keepFolder -File | Where-Object {
        $_.Extension -eq '.lib' -or (
            $_.Extension -eq '.tcl' -and $_.Name -notin $keepFiles
        )
    } | Remove-Item -Force
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

    if (Test-Path $appDistRoot) {
        Remove-Item -LiteralPath $appDistRoot -Recurse -Force
    }

    New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
    Invoke-Step -Action { python -m PyInstaller --clean --noconfirm $specPath } -FailureMessage 'PyInstaller build failed.'

    if (-not (Test-Path $appDistRoot)) {
        throw "Expected packaged app folder was not created: $appDistRoot"
    }

    Prune-WindowsReleaseArtifacts -TargetRoot $appDistRoot
    Initialize-PackagedRuntimeState -TargetRoot $appDistRoot

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
