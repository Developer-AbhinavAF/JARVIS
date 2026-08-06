# Quick JARVIS Startup
Write-Host "Starting JARVIS..." -ForegroundColor Green

# Kill Python processes
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

# Start Web Interface
Write-Host "Starting Web Interface..." -ForegroundColor Yellow
$webProcess = Start-Process python -ArgumentList "jarvis-desktop/backend/app.py" -NoNewWindow -PassThru
Start-Sleep -Seconds 5

# Pre-warm LLM
Write-Host "Pre-warming LLM..." -ForegroundColor Yellow
try {
    $body = @{message = "hello"} | ConvertTo-Json
    Invoke-WebRequest -Uri "http://localhost:8001/query" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 90 | Out-Null
    Write-Host "LLM Pre-warmed" -ForegroundColor Green
} catch {
    Write-Host "LLM Pre-warm timeout (normal for large models)" -ForegroundColor Yellow
}

# Start Telephony Server
Write-Host "Starting Telephony Server..." -ForegroundColor Yellow
$telephonyProcess = Start-Process python -ArgumentList "-m interface.telephony.twilio_server" -NoNewWindow -PassThru
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JARVIS Running" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Web: http://localhost:8001" -ForegroundColor White
Write-Host "Telephony: http://localhost:8100/voice/health" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Stop ngrok and run: ngrok http 8001" -ForegroundColor White
Write-Host "2. Update .env with new ngrok URL" -ForegroundColor White
Write-Host "3. Restart telephony server" -ForegroundColor White
Write-Host ""
Write-Host "Stop: Stop-Process -Id $($webProcess.Id), $($telephonyProcess.Id)" -ForegroundColor Red
Write-Host ""
