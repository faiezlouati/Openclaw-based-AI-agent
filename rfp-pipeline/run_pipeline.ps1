# RFP Pipeline — run all steps in sequence

$venvPython = ".\venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: venv not found. Run setup-python.ps1 first and install requirements." -ForegroundColor Red
    exit 1
}

$steps = @(
    "step1_parse.py",
    "step2_clean.py",
    "step3_chunk.py",
    "step4_embed.py",
    "step5_analyse.py"
)

foreach ($step in $steps) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Running $step" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan

    & $venvPython $step

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "FAILED: $step exited with code $LASTEXITCODE. Stopping." -ForegroundColor Red
        exit $LASTEXITCODE
    }

    Write-Host "DONE: $step" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All steps completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
