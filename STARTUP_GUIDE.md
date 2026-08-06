# JARVIS Web + Phone Startup Guide

## Quick Start (3 Steps)

### Step 1: Run the startup script
```powershell
cd E:\AI\JARVIS
.\start_jarvis.ps1
```

### Step 2: Fix ngrok
- Stop your current ngrok (Ctrl+C)
- Start ngrok pointing to port 8001:
```powershell
ngrok http 8001
```

### Step 3: Update .env
- Copy your new ngrok URL (e.g., https://abc123.ngrok-free.dev)
- Edit `.env` line 79:
```bash
TWILIO_WEBHOOK=https://abc123.ngrok-free.dev
```

### Step 4: Restart telephony server
- Stop the telephony server (Ctrl+C in its terminal)
- Restart it:
```powershell
python -m interface.telephony.twilio_server
```

## Manual Startup (If script fails)

### Terminal 1: Web Interface
```powershell
cd E:\AI\JARVIS
python jarvis-desktop/backend/app.py
```

### Terminal 2: Telephony Server
```powershell
cd E:\AI\JARVIS
python -m interface.telephony.twilio_server
```

### Terminal 3: ngrok
```powershell
ngrok http 8001
```

## Testing

### Test Web Interface
Open browser: http://localhost:8001

### Test Telephony
```powershell
curl http://localhost:8100/voice/health
```

### Make a Phone Call
Call: +15043851657

## Troubleshooting

### If web interface fails to start
```powershell
# Kill process on port 8001
$process = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($process) { Stop-Process -Id $process -Force }
```

### If telephony server fails to start
```powershell
# Kill process on port 8100
$process = Get-NetTCPConnection -LocalPort 8100 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($process) { Stop-Process -Id $process -Force }
```

### If ngrok shows connection refused
- Make sure web interface is running on port 8001
- Make sure ngrok is pointing to port 8001 (not 8000)

## Port Summary
- **8001**: Web Interface (JARVIS Desktop Backend)
- **8100**: Telephony Server (Twilio Voice)
- **8000**: NOT USED (ngrok was pointing here incorrectly)

## Important Notes
- Web interface does NOT have /health endpoint - use root URL for testing
- Telephony server may take 5-10 seconds to fully start
- Always restart telephony server after changing TWILIO_WEBHOOK
- Keep all 3 terminals open (web, telephony, ngrok)
