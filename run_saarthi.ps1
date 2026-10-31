# SAARTHI One-Click Startup Script for Windows PowerShell
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Starting SAARTHI Autonomous Resolution " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check Python environment
if (Test-Path ".venv\Scripts\python.exe") {
    $pythonCmd = ".\.venv\Scripts\python.exe"
} else {
    $pythonCmd = "python"
}

# Start Backend
Write-Host "[1/2] Starting Backend API on http://localhost:8000..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath $pythonCmd -ArgumentList "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000" -PassThru

# Start Frontend
Write-Host "[2/2] Starting Frontend UI on http://localhost:5173..." -ForegroundColor Green
Set-Location frontend
$frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev -- --port 5173 --host" -PassThru
Set-Location ..

Write-Host ""
Write-Host "SAARTHI is running!" -ForegroundColor Green
Write-Host "Customer Chat & Admin: http://localhost:5173" -ForegroundColor White
Write-Host "Backend API & Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "Simulated Core Switch: http://localhost:8000/payments-core/transactions" -ForegroundColor White
Write-Host "Press Ctrl+C or close windows to terminate." -ForegroundColor Gray

