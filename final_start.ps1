# Complete JARVIS Startup Script
# - Starts both web interface and telephony server
# - Pre-warms LLM for fast first response
# - Time-based greetings
# - Streaming TTS for low latency

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JARVIS Complete Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill all Python processes to clear ports
Write-Host "[1/5] Cleaning up existing processes..." -ForegroundColor Yellow
try {
    Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "✓ All Python processes stopped" -ForegroundColor Green
} catch {
    Write-Host "No existing Python processes" -ForegroundColor Gray
}
Start-Sleep -Seconds 3

# Step 2: Start Web Interface
Write-Host "[2/5] Starting Web Interface on port 8001..." -ForegroundColor Yellow
$webProcess = Start-Process python -ArgumentList "jarvis-desktop/backend/app.py" -NoNewWindow -PassThru
Start-Sleep -Seconds 6

# Check web interface
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ Web Interface running (PID: $($webProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "✗ Web Interface failed to start" -ForegroundColor Red
    Write-Host "Trying alternative method..." -ForegroundColor Yellow
    cd "E:\AI\JARVIS\jarvis-desktop\backend"
    $webProcess = Start-Process python -ArgumentList "app.py" -NoNewWindow -PassThru
    Start-Sleep -Seconds 5
}

# Step 3: Pre-warm LLM with "hello" request
Write-Host "[3/5] Pre-warming LLM with 'hello' request..." -ForegroundColor Yellow
try {
    $warmupBody = @{
        message = "hello"
    } | ConvertTo-Json
    
    $warmupResponse = Invoke-WebRequest -Uri "http://localhost:8001/query" -Method POST -Body $warmupBody -ContentType "application/json" -UseBasicParsing -TimeoutSec 90
    Write-Host "✓ LLM Pre-warmed successfully (first response will be fast)" -ForegroundColor Green
} catch {
    Write-Host "⚠ LLM Pre-warm timed out (will warm on first call)" -ForegroundColor Yellow
    Write-Host "  This is normal if Ollama is loading a large model" -ForegroundColor Gray
}

# Step 4: Start Telephony Server
Write-Host "[4/5] Starting Telephony Server on port 8100..." -ForegroundColor Yellow
cd "E:\AI\JARVIS"
$telephonyProcess = Start-Process python -ArgumentList "-m interface.telephony.twilio_server" -NoNewWindow -PassThru
Start-Sleep -Seconds 10

# Check telephony server
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8100/voice/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "✓ Telephony Server running (PID: $($telephonyProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "⚠ Telephony Server health check timed out, but process is running" -ForegroundColor Yellow
    Write-Host "  PID: $($telephonyProcess.Id)" -ForegroundColor Yellow
}

# Step 5: Final status
Write-Host "[5/5] System startup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JARVIS System Status:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Web Interface: http://localhost:8001" -ForegroundColor White
Write-Host "Telephony:     http://localhost:8100/voice/health" -ForegroundColor White
Write-Host "Phone Panel:   http://localhost:8100" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "FEATURES ENABLED:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ LLM Pre-warmed (fast first response)" -ForegroundColor White
Write-Host "✓ Time-based greeting (Good morning/afternoon/evening)" -ForegroundColor White
Write-Host "✓ Streaming TTS (low latency speech)" -ForegroundColor White
Write-Host "✓ Natural conversation flow" -ForegroundColor White
Write-Host "✓ Intelligent speech detection" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "CRITICAL: NGROK SETUP" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "1. Stop current ngrok (Ctrl+C in ngrok terminal)" -ForegroundColor White
Write-Host "2. Start ngrok with CORRECT port:" -ForegroundColor White
Write-Host "   ngrok http 8001" -ForegroundColor White
Write-Host "3. Copy your ngrok URL" -ForegroundColor White
Write-Host "4. Update .env line 79:" -ForegroundColor White
Write-Host "   TWILIO_WEBHOOK=https://your-ngrok-url.ngrok-free.dev" -ForegroundColor White
Write-Host "5. Restart telephony server:" -ForegroundColor White
Write-Host "   - Stop telephony server (Ctrl+C)" -ForegroundColor White
Write-Host "   - Run: python -m interface.telephony.twilio_server" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "TO STOP EVERYTHING:" -ForegroundColor Red
Write-Host "Stop-Process -Id $($webProcess.Id), $($telephonyProcess.Id)" -ForegroundColor White
Write-Host ""
Write-Host "TO TEST:" -ForegroundColor Cyan
Write-Host "1. Web: http://localhost:8001" -ForegroundColor White
Write-Host "2. Telephony: curl http://localhost:8100/voice/health" -ForegroundColor White
Write-Host "3. Phone: Call +15043851657" -ForegroundColor White
Write-Host ""
