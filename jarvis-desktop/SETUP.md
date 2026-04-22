# 🚀 JARVIS Ultimate - Setup Guide

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

1. **Node.js** (v18.0.0 or higher)
   - Download: https://nodejs.org/
   - Verify: `node --version`

2. **Python** (v3.9 or higher)
   - Download: https://python.org/
   - Verify: `python --version` (or `python3 --version` on macOS/Linux)

3. **Git**
   - Download: https://git-scm.com/
   - Verify: `git --version`

4. **npm** (comes with Node.js)
   - Verify: `npm --version`

### Optional but Recommended

- **VS Code** with extensions:
  - ESLint
  - Prettier
  - Python
  - Tailwind CSS IntelliSense

---

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/jarvis-ultimate.git
cd jarvis-desktop
```

### Step 2: Install Dependencies

Run the setup command:

```bash
npm run install:all
```

This command will:
1. Install root project dependencies
2. Install frontend dependencies (React, Vite, etc.)
3. Install Electron dependencies
4. Install Python backend dependencies

**Manual installation** (if the above fails):

```bash
# Root dependencies
npm install

# Frontend
cd frontend && npm install && cd ..

# Electron
cd electron && npm install && cd ..

# Backend (Python)
cd backend
pip install -r requirements.txt
cd ..
```

---

## 🎮 Running the Application

### Development Mode

Start all services with a single command:

```bash
npm run dev
```

This will:
- Start the React frontend (http://localhost:3000)
- Start the FastAPI backend (http://localhost:8000)
- Launch the Electron window

**Access points:**
- 🎨 Frontend: http://localhost:3000
- ⚡ API Docs: http://localhost:8000/docs
- 🔌 WebSocket: ws://localhost:8000/ws

### Running Components Separately

If you need to run components individually:

```bash
# Terminal 1: Frontend
cd frontend && npm run dev

# Terminal 2: Backend
cd backend && python main.py

# Terminal 3: Electron (after frontend is running)
cd electron && npm run dev
```

---

## 🔨 Building for Production

### Windows (.exe installer)

```bash
npm run dist:win
```

Output locations:
- Installer: `electron/dist/JARVIS Ultimate Setup.exe`
- Portable: `electron/dist/JARVIS Ultimate.exe`

### macOS (.dmg)

```bash
npm run dist:mac
```

Output: `electron/dist/JARVIS Ultimate.dmg`

### Linux (.AppImage)

```bash
npm run dist:linux
```

Output: `electron/dist/JARVIS Ultimate.AppImage`

### Build for All Platforms

```bash
npm run dist
```

---

## ⚙️ Configuration

### Frontend Configuration

Create a `.env` file in the `frontend` directory:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

### Backend Configuration

Edit `backend/main.py` to change:
- **Port**: Change `port=8000` in the `uvicorn.run()` call
- **AI Integration**: Extend `AIChatHandler.process_message()`
- **CORS origins**: Modify `allow_origins` in CORS middleware

### Electron Configuration

Settings are automatically persisted. To customize:

1. **Window size**: Edit `electron/main.js` - `createWindow()` function
2. **Icons**: Replace files in `electron/assets/`
3. **Menu**: Modify the `Menu.buildFromTemplate()` call

---

## 🧪 Testing

### Frontend Tests

```bash
cd frontend
npm run test
```

### Backend Tests

```bash
cd backend
python -m pytest  # (if tests are added)
```

### Manual Testing Checklist

- [ ] App launches without errors
- [ ] Frontend connects to backend (check console)
- [ ] WebSocket connects (real-time updates work)
- [ ] Text mode chat works
- [ ] Speech mode toggle works
- [ ] System stats display correctly
- [ ] Plugins panel shows status
- [ ] Quick actions work
- [ ] Window controls (minimize, maximize, close)
- [ ] System tray icon appears
- [ ] Tray menu functions work

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "Cannot find module 'X'"

```bash
# Clear npm cache and reinstall
npm cache clean --force
rm -rf node_modules frontend/node_modules electron/node_modules
npm run install:all
```

#### 2. Backend won't start

```bash
# Check Python installation
python --version

# Install dependencies manually
cd backend
pip install -r requirements.txt

# Check for port conflicts
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS/Linux
```

#### 3. Frontend can't connect to backend

- Verify backend is running: `curl http://localhost:8000/`
- Check firewall settings
- Ensure ports 3000 and 8000 are available
- Check browser console for CORS errors

#### 4. Electron window is blank

```bash
# Frontend must be running first
npm run dev:frontend

# Then in another terminal
npm run dev:electron
```

#### 5. Build fails

```bash
# Clean everything
npm run clean

# Reinstall
npm run install:all

# Try building again
npm run build
```

### Platform-Specific Issues

#### Windows
- **Python not found**: Ensure Python is in PATH, or use `py` instead of `python`
- **Build fails**: Install Visual Studio Build Tools

#### macOS
- **Permission denied**: Use `sudo` for global installs, or fix permissions
- **Python issues**: Use Homebrew Python: `brew install python@3.11`

#### Linux
- **Missing dependencies**: Install build essentials:
  ```bash
  sudo apt-get install build-essential libgtk-3-dev
  ```

---

## 📝 Environment-Specific Notes

### Windows Development

1. Use PowerShell or Command Prompt (not WSL for Electron)
2. Python command may be `python` or `py`
3. Install Windows Build Tools if building native modules:
   ```bash
   npm install --global windows-build-tools
   ```

### macOS Development

1. Install Xcode Command Line Tools:
   ```bash
   xcode-select --install
   ```
2. May need to allow app in Security & Privacy settings
3. Code signing for distribution requires Apple Developer account

### Linux Development

1. Install dependencies:
   ```bash
   sudo apt-get install build-essential libgtk-3-dev libgconf-2-4
   ```
2. For AppImage to work, install FUSE:
   ```bash
   sudo apt-get install libfuse2
   ```

---

## 🔐 Security Notes

- Never commit `.env` files with real credentials
- Backend runs on localhost only by default
- IPC communications are context-isolated
- Only whitelisted system commands can be executed

---

## 📚 Additional Resources

- [React Documentation](https://react.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Electron Documentation](https://www.electronjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Framer Motion Documentation](https://www.framer.com/motion/)

---

## ✅ Next Steps

After successful setup:

1. Customize the theme colors in `frontend/src/index.css`
2. Add your AI model integration in `backend/main.py`
3. Create additional plugins in `frontend/src/store/useStore.ts`
4. Build and distribute your application!

For questions or issues, please check the [README.md](README.md) or open an issue on GitHub.

---

**Happy building! 🚀**
