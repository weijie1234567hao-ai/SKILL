#!/usr/bin/env powershell
# install_deps.ps1 - Install Python dependencies for pdf2md-cleaner
# Run: powershell -ExecutionPolicy Bypass -File install_deps.ps1

param(
    [switch]$All,
    [switch]$MinerU,
    [switch]$Marker,
    [switch]$Docling,
    [switch]$PyMuPDF4LLM,
    [switch]$Lightweight
)

$ErrorActionPreference = "Stop"

function Install-PipPackage {
    param([string]$Name, [string]$InstallCmd)
    Write-Host "Installing $Name ..." -ForegroundColor Cyan
    python -m pip install $InstallCmd.Split(" ") 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $Name installed" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] $Name install failed (may need manual install)" -ForegroundColor Yellow
    }
}

# Default: lightweight (PyMuPDF4LLM only, no GPU needed)
if (-not ($All -or $MinerU -or $Marker -or $Docling -or $PyMuPDF4LLM -or $Lightweight)) {
    $Lightweight = $true
}

Write-Host "========================================" -ForegroundColor White
Write-Host "  PDF2MD-Cleaner Dependency Installer" -ForegroundColor White
Write-Host "========================================" -ForegroundColor White

# Always install PyMuPDF4LLM (lightweight, no GPU)
if ($PyMuPDF4LLM -or $Lightweight -or $All) {
    Install-PipPackage "PyMuPDF4LLM" "pymupdf4llm"
}

# Docling (good table extraction, CPU-friendly)
if ($Docling -or $All) {
    Install-PipPackage "Docling" "docling"
}

# Marker (GPU recommended, high accuracy)
if ($Marker -or $All) {
    Write-Host "Note: Marker requires PyTorch (will install if missing)" -ForegroundColor Yellow
    Install-PipPackage "Marker-PDF" "marker-pdf"
}

# MinerU (most powerful, needs models download)
if ($MinerU -or $All) {
    Write-Host "Note: MinerU needs model weights download after install" -ForegroundColor Yellow
    Install-PipPackage "MinerU" '-U "magic-pdf[full]" --extra-index-url https://wheels.myhloli.com'
}

Write-Host ""
Write-Host "Done! Recommended backends:" -ForegroundColor Green
Write-Host "  - Lightweight (CPU only): pymupdf4llm" -ForegroundColor White
Write-Host "  - Best quality (CPU):     docling" -ForegroundColor White
Write-Host "  - Best accuracy (GPU):    marker" -ForegroundColor White
Write-Host "  - Most powerful (GPU):    mineru" -ForegroundColor White
