# Install the FlashForge Creator 3 profile into OrcaSlicer on Windows.
#
# Run from an elevated PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\install_windows.ps1
#
# Uninstall:
#   .\install_windows.ps1 -Uninstall
#
# Dry run (print what would happen, no changes):
#   .\install_windows.ps1 -DryRun

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$DryRun,
    [string]$OrcaRoot = "$Env:ProgramFiles\OrcaSlicer"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$profilesDir = Join-Path $OrcaRoot "resources\profiles"
$vendorFile = Join-Path $profilesDir "FlashForge.json"
$vendorDir  = Join-Path $profilesDir "FlashForge"
$backupSuffix = ".bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

function Invoke-Step($description, [scriptblock]$action) {
    if ($DryRun) {
        Write-Host "[dry-run] $description"
    } else {
        Write-Host $description
        & $action
    }
}

if (-not (Test-Path $OrcaRoot)) {
    Write-Error "OrcaSlicer not found at $OrcaRoot. Install from https://github.com/SoftFever/OrcaSlicer/releases first, or pass -OrcaRoot <path>."
    exit 1
}

if ($Uninstall) {
    Write-Host "Uninstalling FlashForge Creator 3 profile from OrcaSlicer..."
    if (Test-Path $vendorFile) {
        Invoke-Step "Removing $vendorFile" { Remove-Item -Force $vendorFile }
    }
    if (Test-Path $vendorDir) {
        Invoke-Step "Removing $vendorDir" { Remove-Item -Recurse -Force $vendorDir }
    }
    Write-Host "Done. Restart OrcaSlicer."
    exit 0
}

Write-Host "Installing FlashForge Creator 3 profile into:"
Write-Host "  $profilesDir"
Write-Host ""

if (Test-Path $vendorFile) {
    Invoke-Step "Backing up FlashForge.json -> FlashForge.json$backupSuffix" {
        Copy-Item -Force $vendorFile ($vendorFile + $backupSuffix)
    }
}
if (Test-Path $vendorDir) {
    Invoke-Step "Backing up FlashForge\ -> FlashForge$backupSuffix" {
        Copy-Item -Recurse -Force $vendorDir ($vendorDir + $backupSuffix)
    }
}

Invoke-Step "Creating vendor directory tree" {
    New-Item -ItemType Directory -Force -Path (Join-Path $vendorDir "machine")  | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $vendorDir "process")  | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $vendorDir "filament") | Out-Null
}

Invoke-Step "Copying FlashForge.json" {
    Copy-Item -Force (Join-Path $here "FlashForge.json") $vendorFile
}
Invoke-Step "Copying machine/*.json" {
    Copy-Item -Force (Join-Path $here "machine\*.json") (Join-Path $vendorDir "machine")
}
Invoke-Step "Copying process/*.json" {
    Copy-Item -Force (Join-Path $here "process\*.json") (Join-Path $vendorDir "process")
}
Invoke-Step "Copying filament/*.json" {
    Copy-Item -Force (Join-Path $here "filament\*.json") (Join-Path $vendorDir "filament")
}

$scriptsAbs = Join-Path $here "scripts"
Write-Host ""
Write-Host "Installed. Restart OrcaSlicer, then:"
Write-Host "  1. Settings -> Printers -> + Add -> vendor 'FlashForge' -> Creator 3"
Write-Host "  2. Settings -> Others -> set 'Post-processing scripts' to:"
Write-Host "       python ""$scriptsAbs\gx_converter.py"""
Write-Host "     (Python 3 from python.org must be on PATH.)"
Write-Host "  3. Read $here\README.md for IDEX (left/right/mirror) usage."
