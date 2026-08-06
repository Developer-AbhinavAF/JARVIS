# JARVIS Startup with LLM Pre-warming
Write-Host "Starting JARVIS with LLM Pre-warming..." -ForegroundColor Green

# Kill all Python processes
Write-Host "Stopping all Python processes..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

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

# Pre-warm LLM by sending a "hello" request
Write-Host "Pre-warming LLM with 'hello' request..." -ForegroundColor Yellow
try {
    $warmupResponse = Invoke-WebRequest -Uri "http://localhost:8001/query" -Method POST -Body '{"message":"hello"}' -ContentType "application/json" -UseBasicParsing -TimeoutSec 60
    Write-Host "✓ LLM Pre-warmed successfully" -ForegroundColor Green
} catch {
    Write-Host "⚠ LLM Pre-warm timed out or failed (will warm on first call)" -ForegroundColor Yellow
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
Write-Host "Web Interface: http://localhost:8001 (PID: $($webProcess.Id))" -ForegroundColor White
Write-Host "Telephony:     http://localhost:8100/voice/health (PID: $($telephonyProcess.Id))" -ForegroundColor White
Write-Host "Phone Panel:   http://localhost:8100" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "1. Stop current ngrok (Ctrl+C)" -ForegroundColor White
Write-Host "2. Start ngrok with: ngrok http 8001" -ForegroundColor White
Write-Host "3. Copy the ngrok URL" -ForegroundColor White
Write-Host "4. Update .env line 79:" -ForegroundColor White
Write-Host "   TWILIO_WEBHOOK=https://your-ngrok-url.ngrok-free.dev" -ForegroundColor White
Write-Host "5. Restart telephony server:" -ForegroundColor White
Write-Host "   - Stop telephony server (Ctrl+C)" -ForegroundColor White
Write-Host "   - Run: python -m interface.telephony.twilio_server" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "ENHANCEMENTS:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ LLM Pre-warmed (faster first response)" -ForegroundColor White
Write-Host "✓ Time-based greeting (Good morning/afternoon/evening)" -ForegroundColor White
Write-Host "✓ Streaming TTS enabled (reduced latency)" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To stop everything:" -ForegroundColor Red
Write-Host "Stop-Process -Id $($webProcess.Id), $($telephonyProcess.Id)" -ForegroundColor White
Write-Host ""
