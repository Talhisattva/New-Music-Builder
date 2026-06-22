param(
    [switch]$SkipValidation
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$distRoot = Join-Path $repoRoot 'dist'
$releaseRoot = Join-Path $repoRoot 'release'
$specPath = Join-Path $repoRoot 'NewMusicBuilder.spec'
$appDistRoot = Join-Path $distRoot 'NewMusicBuilder'
$sourcePackScript = Join-Path $repoRoot 'tools\build_source_release.py'

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

    $zipPath = Join-Path $releaseRoot "NewMusicBuilder-v$version-win64.zip"
    if (Test-Path $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Compress-Archive -Path $appDistRoot -DestinationPath $zipPath -CompressionLevel Optimal

    $sourceZipPath = Join-Path $releaseRoot "NewMusicBuilder-v$version-source.zip"
    Invoke-Step -Action { python $sourcePackScript --repo-root $repoRoot --output $sourceZipPath | Out-Null } -FailureMessage 'Source release packaging failed.'

    Write-Host "Windows release package created: $zipPath"
    Write-Host "Source release package created: $sourceZipPath"
}
finally {
    Pop-Location
}
