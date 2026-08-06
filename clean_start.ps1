# Clean JARVIS Startup Script
Write-Host "Cleaning up and starting JARVIS..." -ForegroundColor Green

# Kill all Python processes
Write-Host "Stopping all Python processes..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Wait for ports to be released
Write-Host "Waiting for ports to be released..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start Web Interface
Write-Host "Starting Web Interface on port 8001..." -ForegroundColor Green
$webProcess = Start-Process python -ArgumentList "jarvis-desktop/backend/app.py" -NoNewWindow -PassThru
Start-Sleep -Seconds 5

# Check web interface
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ Web Interface running (PID: $($webProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "✗ Web Interface failed to start" -ForegroundColor Red
}

# Start Telephony Server
Write-Host "Starting Telephony Server on port 8100..." -ForegroundColor Green
$telephonyProcess = Start-Process python -ArgumentList "-m interface.telephony.twilio_server" -NoNewWindow -PassThru
Start-Sleep -Seconds 8

# Check telephony server
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8100/voice/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "✓ Telephony Server running (PID: $($telephonyProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "⚠ Telephony Server starting up (PID: $($telephonyProcess.Id))" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JARVIS System Running:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Web Interface: http://localhost:8001" -ForegroundColor White
Write-Host "Telephony:     http://localhost:8100/voice/health" -ForegroundColor White
Write-Host "Phone Panel:   http://localhost:8100" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CRITICAL NEXT STEPS:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "1. Stop current ngrok (Ctrl+C)" -ForegroundColor White
Write-Host "2. Start ngrok with CORRECT port:" -ForegroundColor White
Write-Host "   ngrok http 8001" -ForegroundColor White
Write-Host "3. Copy your ngrok URL" -ForegroundColor White
Write-Host "4. Update .env line 79:" -ForegroundColor White
Write-Host "   TWILIO_WEBHOOK=https://your-ngrok-url.ngrok-free.dev" -ForegroundColor White
Write-Host "5. Restart telephony server:" -ForegroundColor White
Write-Host "   - Stop this script" -ForegroundColor White
Write-Host "   - Run: python -m interface.telephony.twilio_server" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop everything:" -ForegroundColor Red
Write-Host "Stop-Process -Id $($webProcess.Id), $($telephonyProcess.Id)" -ForegroundColor White
Write-Host ""
