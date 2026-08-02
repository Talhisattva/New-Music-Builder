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

function Prune-WindowsReleaseArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetRoot
    )

    $targetPath = [System.IO.Path]::GetFullPath($TargetRoot)

    Get-ChildItem -Path $targetPath -Recurse -Force -File -Filter '.DS_Store' -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue

    Get-ChildItem -Path $targetPath -Recurse -Force -Directory -Filter '*.dist-info' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    Get-ChildItem -Path $targetPath -Recurse -Force -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

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

function New-StagedReleaseRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceRoot,
        [Parameter(Mandatory = $true)]
        [string]$StageRoot,
        [Parameter(Mandatory = $true)]
        [string]$FolderName
    )

    if (Test-Path $StageRoot) {
        Remove-Item -LiteralPath $StageRoot -Recurse -Force
    }

    $stageFolder = Join-Path $StageRoot $FolderName
    New-Item -ItemType Directory -Path $stageFolder -Force | Out-Null

    $allowedTopLevel = @(
        'NewMusicBuilder.exe',
        '_internal'
    )

    foreach ($name in $allowedTopLevel) {
        $source = Join-Path $SourceRoot $name
        if (-not (Test-Path $source)) {
            throw "Expected packaged release entry was not found: $source"
        }
        Copy-Item -LiteralPath $source -Destination $stageFolder -Recurse -Force
    }

    return $stageFolder
}

function Assert-ReleaseLayout {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetRoot
    )

    $targetPath = [System.IO.Path]::GetFullPath($TargetRoot)
    $forbidden = @(
        'workspace',
        'logs',
        'Generated Textures'
    )

    foreach ($entry in $forbidden) {
        $path = Join-Path $targetPath $entry
        if (Test-Path $path) {
            throw "Packaged app should not ship pre-seeded runtime state: $path"
        }
    }

    $required = @(
        'NewMusicBuilder.exe',
        '_internal'
    )

    foreach ($entry in $required) {
        $path = Join-Path $targetPath $entry
        if (-not (Test-Path $path)) {
            throw "Packaged app is missing required release content: $path"
        }
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

    Prune-WindowsReleaseArtifacts -TargetRoot $appDistRoot

    $stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) "NewMusicBuilder-release-$version"
    $stageFolder = New-StagedReleaseRoot -SourceRoot $appDistRoot -StageRoot $stageRoot -FolderName 'NewMusicBuilder'
    Assert-ReleaseLayout -TargetRoot $stageFolder

    $zipPath = Join-Path $releaseRoot "NewMusicBuilder-v$version-win64.zip"
    if (Test-Path $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Compress-Archive -Path (Join-Path $stageRoot '*') -DestinationPath $zipPath -CompressionLevel Optimal

    if (Test-Path $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }

    Write-Host "Windows release package created: $zipPath"
    Write-Host 'Reminder: verify first-run AppData initialization, then submit any remaining false positives to Microsoft Defender and Bkav.'
}
finally {
    Pop-Location
}
