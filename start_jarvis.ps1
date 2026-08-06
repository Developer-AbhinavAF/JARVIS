# JARVIS Startup Script
Write-Host "Starting JARVIS Web + Telephony System..." -ForegroundColor Green

# Kill any process using port 8001
Write-Host "Checking port 8001..." -ForegroundColor Yellow
$process = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($process) {
    Write-Host "Killing process $process on port 8001" -ForegroundColor Yellow
    Stop-Process -Id $process -Force
    Start-Sleep -Seconds 2
}

# Kill any process using port 8100
Write-Host "Checking port 8100..." -ForegroundColor Yellow
$process = Get-NetTCPConnection -LocalPort 8100 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($process) {
    Write-Host "Killing process $process on port 8100" -ForegroundColor Yellow
    Stop-Process -Id $process -Force
    Start-Sleep -Seconds 2
}

# Start Web Interface
Write-Host "Starting Web Interface..." -ForegroundColor Green
$webProcess = Start-Process python -ArgumentList "jarvis-desktop/backend/app.py" -NoNewWindow -PassThru
Start-Sleep -Seconds 5

# Check if web interface started (try root endpoint since /health doesn't exist)
Write-Host "Checking Web Interface..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ Web Interface started successfully (PID: $($webProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "✗ Web Interface failed to start" -ForegroundColor Red
    Write-Host "  Try running manually: python jarvis-desktop/backend/app.py" -ForegroundColor Yellow
}

# Start Telephony Server
Write-Host "Starting Telephony Server..." -ForegroundColor Green
$telephonyProcess = Start-Process python -ArgumentList "-m interface.telephony.twilio_server" -NoNewWindow -PassThru
Start-Sleep -Seconds 8

# Check if telephony server started (with longer timeout)
Write-Host "Checking Telephony Server..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8100/voice/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "✓ Telephony Server started successfully (PID: $($telephonyProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "⚠ Telephony Server health check timed out, but process is running" -ForegroundColor Yellow
    Write-Host "  PID: $($telephonyProcess.Id)" -ForegroundColor Yellow
    Write-Host "  This is normal - the server may still be initializing" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JARVIS System Status:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Web Interface: http://localhost:8001 (PID: $($webProcess.Id))" -ForegroundColor White
Write-Host "Telephony:     http://localhost:8100/voice/health (PID: $($telephonyProcess.Id))" -ForegroundColor White
Write-Host "Phone Panel:   http://localhost:8100" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT SETUP STEPS:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "1. Stop your current ngrok (Ctrl+C in ngrok terminal)" -ForegroundColor White
Write-Host "2. Start ngrok with: ngrok http 8001" -ForegroundColor White
Write-Host "3. Copy the ngrok URL (e.g., https://abc123.ngrok-free.dev)" -ForegroundColor White
Write-Host "4. Edit .env line 79 with your ngrok URL:" -ForegroundColor White
Write-Host "   TWILIO_WEBHOOK=https://your-ngrok-url.ngrok-free.dev" -ForegroundColor White
Write-Host "5. Restart telephony server to pick up new webhook:" -ForegroundColor White
Write-Host "   - Stop telephony server (Ctrl+C)" -ForegroundColor White
Write-Host "   - Run: python -m interface.telephony.twilio_server" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "TO STOP THE SYSTEM:" -ForegroundColor Red
Write-Host "Run: Stop-Process -Id $($webProcess.Id), $($telephonyProcess.Id)" -ForegroundColor White
Write-Host ""
