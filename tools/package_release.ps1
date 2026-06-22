param(
    [switch]$SkipValidation
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$distRoot = Join-Path $repoRoot 'dist'
$releaseRoot = Join-Path $repoRoot 'release'
$specPath = Join-Path $repoRoot 'NewMusicBuilder.spec'
$appDistRoot = Join-Path $distRoot 'NewMusicBuilder'

Push-Location $repoRoot
try {
    $version = python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('src').resolve())); import new_music_builder; print(new_music_builder.__version__)"
    if (-not $version) {
        throw 'Unable to resolve app version.'
    }

    python -m PyInstaller --version | Out-Null

    if (-not $SkipValidation) {
        python -m compileall src
        pytest -q
    }

    if (Test-Path $appDistRoot) {
        Remove-Item -LiteralPath $appDistRoot -Recurse -Force
    }

    New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
    python -m PyInstaller --clean --noconfirm $specPath

    if (-not (Test-Path $appDistRoot)) {
        throw "Expected packaged app folder was not created: $appDistRoot"
    }

    $zipPath = Join-Path $releaseRoot "NewMusicBuilder-v$version-win64.zip"
    if (Test-Path $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Compress-Archive -Path $appDistRoot -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Host "Release package created: $zipPath"
}
finally {
    Pop-Location
}
