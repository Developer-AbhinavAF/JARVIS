# 🤖 JARVIS Ultimate - Desktop AI Assistant

A futuristic, production-ready desktop AI assistant built with **React**, **FastAPI**, and **Electron**. Features a stunning glassmorphism UI inspired by Iron Man's JARVIS with real-time system monitoring, voice/text modes, and modular plugin architecture.

![JARVIS Ultimate](https://i.imgur.com/your-screenshot.png)

## ✨ Features

### 🎨 Design
- **Dark futuristic UI** - Iron Man JARVIS inspired design
- **Glassmorphism panels** - Backdrop blur and transparency effects
- **Neon glow accents** - Red (#ff3b3b) for text mode, Pink (#ff6ec7) for speech mode
- **Smooth animations** - Framer Motion powered transitions
- **Animated waveform** - Real-time voice visualization

### 💬 AI Capabilities
- **Dual Mode Operation**
  - 📝 **Text Mode**: ChatGPT-style conversation
  - 🎤 **Speech Mode**: Voice-activated AI with animated waveform
- **Real-time Chat**: WebSocket powered instant messaging
- **System Integration**: Monitor CPU, RAM, Battery, Network, Processes
- **Quick Actions**: Screenshots, YouTube, Reminders, Daily Briefing

### 🔌 Plugin System
- Vision (Webcam, QR, Motion Detection)
- OCR (Image & Screen Text Recognition)
- File AI (PDF, DOCX, Excel processing)
- Browser Agent (Web automation)
- Local LLM (Run local AI models)

### 🖥️ System Dashboard
- Real-time CPU, RAM, Battery monitoring
- Network speed tracking
- Process management
- Mini charts for each metric

### ⚡ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + TypeScript + Vite |
| **Styling** | Tailwind CSS + Framer Motion |
| **State** | Zustand (persistent) |
| **Charts** | Recharts |
| **Backend** | FastAPI (Python) |
| **Real-time** | WebSocket |
| **Desktop** | Electron |
| **System** | psutil, pyautogui |

## 🚀 Quick Start

### Prerequisites
- **Node.js** 18+ and npm
- **Python** 3.9+
- **Git**

### Installation

1. **Clone and navigate to the project:**
```bash
git clone https://github.com/yourusername/jarvis-ultimate.git
cd jarvis-ultimate
```

2. **Install all dependencies:**
```bash
npm run install:all
```

This installs:
- Root dev dependencies
- Frontend (React + Vite)
- Electron wrapper
- Backend Python packages

### Development

Run all components simultaneously:

```bash
npm run dev
```

This starts:
- 🎨 Frontend dev server (http://localhost:3000)
- ⚡ Backend API server (http://localhost:8000)
- 🖥️ Electron window (loads frontend)

Or run individually:
```bash
npm run dev:frontend  # Frontend only
npm run dev:backend   # Backend only
npm run dev:electron  # Electron only (requires frontend running)
```

### Building for Production

#### Windows (.exe)
```bash
npm run dist:win
```
Output: `electron/dist/JARVIS Ultimate Setup.exe`

#### macOS (.dmg)
```bash
npm run dist:mac
```
Output: `electron/dist/JARVIS Ultimate.dmg`

#### Linux (.AppImage)
```bash
npm run dist:linux
```
Output: `electron/dist/JARVIS Ultimate.AppImage`

#### All Platforms
```bash
npm run dist
```

## 📁 Project Structure

```
jarvis-desktop/
├── frontend/                 # React Application
│   ├── src/
│   │   ├── components/      # UI Components
│   │   │   ├── Sidebar.tsx  # Left navigation
│   │   │   ├── TopBar.tsx   # Mode toggle + waveform
│   │   │   ├── ChatPanel.tsx # Main chat interface
│   │   │   ├── RightPanel.tsx # System stats + plugins
│   │   │   ├── BottomBar.tsx  # Quick actions
│   │   │   └── Waveform.tsx   # Animated voice visualizer
│   │   ├── store/
│   │   │   └── useStore.ts  # Zustand state management
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts # Real-time communication
│   │   │   └── useApi.ts    # API calls
│   │   ├── types/
│   │   │   └── index.ts     # TypeScript definitions
│   │   ├── App.tsx          # Main app component
│   │   └── index.css        # Global styles
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                  # FastAPI Backend
│   ├── main.py              # API server + WebSocket
│   └── requirements.txt
│
├── electron/                 # Desktop Wrapper
│   ├── main.js              # Electron main process
│   ├── preload.js           # Secure IPC bridge
│   ├── package.json         # Electron builder config
│   └── assets/              # Icons and resources
│
├── package.json             # Root orchestration
└── README.md
```

## 🛠️ API Endpoints

### REST API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/chat` | POST | Send message to AI |
| `/api/system-stats` | GET | Get current system stats |
| `/api/execute` | POST | Execute system command |
| `/api/plugins` | GET | Get plugin statuses |
| `/api/memory` | GET | Get notes, todos, reminders |

### WebSocket
Connect to `ws://localhost:8000/ws` for real-time updates:
- System stats (every 2 seconds)
- Listening state changes
- Chat responses

Message format:
```json
{
  "type": "system_stats",
  "payload": { ... }
}
```

## 🎨 Customization

### Theme Colors
Edit `frontend/src/index.css`:
```css
:root {
  --jarvis-bg: #0b0b0f;
  --jarvis-accent-red: #ff3b3b;
  --jarvis-accent-pink: #ff6ec7;
}
```

### Adding Plugins
Edit `frontend/src/store/useStore.ts`:
```typescript
plugins: [
  {
    id: 'my-plugin',
    name: 'My Plugin',
    description: 'Does cool things',
    icon: 'IconName',
    status: 'ready',
    version: '1.0.0',
  },
]
```

## 📝 Configuration

### Frontend Environment Variables
Create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
```

### Backend Configuration
Backend settings can be modified in `backend/main.py`:
- Change port: Modify `uvicorn.run(port=8000)`
- Add AI model integration: Extend `AIChatHandler.process_message()`

### Electron Settings
Store persists window state and user preferences automatically.

## 🔒 Security

- Context isolation enabled
- Preload script for secure IPC
- CSP headers in production
- No node integration in renderer
- Allowed commands whitelist for system execution

## 🐛 Troubleshooting

### Frontend won't connect to backend
```bash
# Check if backend is running
curl http://localhost:8000/health

# Restart backend
cd backend && python main.py
```

### Build fails
```bash
# Clean and reinstall
npm run clean
npm run install:all
```

### Electron won't start
```bash
# Check Electron dependencies
cd electron && npm install
cd .. && npm run dev
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Credits

- **Design Inspiration**: Iron Man JARVIS
- **UI Framework**: React + Tailwind CSS
- **Animation**: Framer Motion
- **Icons**: Lucide React
- **System Monitoring**: psutil

---

<p align="center">
  <b>Built with ❤️ by the JARVIS Team</b><br>
  <i>Your personal AI operating system</i>
</p>
