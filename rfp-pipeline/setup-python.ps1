
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Python Setup Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking for Python installation..." -ForegroundColor Yellow

try {
    $pythonCheck = & python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS: Python is installed: $pythonCheck" -ForegroundColor Green
        $pythonInstalled = $true
    } else {
        $pythonInstalled = $false
    }
}
catch {
    $pythonInstalled = $false
}

if (-not $pythonInstalled) {
    Write-Host "WARNING: Python is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python first:" -ForegroundColor Yellow
    Write-Host "1. Go to https://python.org/downloads" -ForegroundColor White
    Write-Host "2. Download Python 3.12 or later" -ForegroundColor White
    Write-Host "3. Run the installer" -ForegroundColor White
    Write-Host "4. IMPORTANT: Check 'Add Python to PATH'" -ForegroundColor Red
    Write-Host "5. Restart your terminal after installation" -ForegroundColor Yellow
    Write-Host ""

    $continue = Read-Host "Do you want to continue without Python? (y/n)"
    if ($continue -ne 'y') {
        Write-Host "Exiting. Please install Python first." -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host ""
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow

    & python -m venv venv

    if (Test-Path "venv") {
        Write-Host "SUCCESS: Virtual environment 'venv' created!" -ForegroundColor Green
        Write-Host ""
        Write-Host "To activate the virtual environment:" -ForegroundColor Cyan
        Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
        Write-Host ""
        Write-Host "After activation, install packages with:" -ForegroundColor Cyan
        Write-Host "  pip install <package-name>" -ForegroundColor White
    }
    else {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
