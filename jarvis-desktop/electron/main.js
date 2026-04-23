/**
 * JARVIS Ultimate - Electron Main Process
 * Desktop wrapper for the AI assistant application
 */

const { app, BrowserWindow, ipcMain, shell, dialog, Tray, Menu, nativeImage } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const log = require('electron-log');
const Store = require('electron-store');

// Configure logging
log.initialize();
Object.assign(console, log.functions);

// Configuration store
const store = new Store();

// Global references
let mainWindow = null;
let backendProcess = null;
let tray = null;
let isQuitting = false;

// Development mode check
const isDev = process.argv.includes('--dev') || !app.isPackaged;

// Paths
const FRONTEND_PATH = isDev
  ? 'http://localhost:3000'
  : path.join(__dirname, '../frontend/dist/index.html');

const BACKEND_PATH = isDev
  ? path.join(__dirname, '../backend/jarvis_api.py')
  : path.join(process.resourcesPath, 'backend/jarvis_api.py');

// ============== WINDOW MANAGEMENT ==============

function createWindow() {
  log.info('Creating main window...');

  const windowState = store.get('windowState', {
    width: 1400,
    height: 900,
    x: undefined,
    y: undefined,
    maximized: false
  });

  mainWindow = new BrowserWindow({
    width: windowState.width,
    height: windowState.height,
    x: windowState.x,
    y: windowState.y,
    minWidth: 1000,
    minHeight: 700,
    title: 'JARVIS Ultimate',
    icon: path.join(__dirname, 'assets/icon.png'),
    show: false, // Don't show until ready
    frame: false, // Custom frame
    titleBarStyle: 'hidden',
    backgroundColor: '#0b0b0f',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: !isDev,
      allowRunningInsecureContent: isDev
    }
  });

  // Load frontend
  if (isDev && FRONTEND_PATH.startsWith('http')) {
    mainWindow.loadURL(FRONTEND_PATH);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(FRONTEND_PATH);
  }

  // Window state management
  mainWindow.once('ready-to-show', () => {
    log.info('Window ready to show');
    
    if (windowState.maximized) {
      mainWindow.maximize();
    }
    
    mainWindow.show();
    
    // Flash frame on Windows to get attention
    if (process.platform === 'win32') {
      mainWindow.flashFrame(true);
      setTimeout(() => mainWindow.flashFrame(false), 3000);
    }
  });

  // Save window state on close
  mainWindow.on('close', (event) => {
    if (!isQuitting && process.platform === 'darwin') {
      event.preventDefault();
      mainWindow.hide();
      return;
    }

    const bounds = mainWindow.getBounds();
    store.set('windowState', {
      width: bounds.width,
      height: bounds.height,
      x: bounds.x,
      y: bounds.y,
      maximized: mainWindow.isMaximized()
    });
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  log.info('Main window created successfully');
}

// ============== BACKEND MANAGEMENT ==============

function startBackend() {
  log.info('Starting Python backend...');

  // Use virtual environment Python
  const venvPath = path.join(__dirname, '../../.venv');
  const pythonExecutable = process.platform === 'win32' 
    ? path.join(venvPath, 'Scripts', 'python.exe')
    : path.join(venvPath, 'bin', 'python');
  
  log.info(`Using Python: ${pythonExecutable}`);
  
  backendProcess = spawn(pythonExecutable, [BACKEND_PATH], {
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
    windowsHide: true,
    cwd: path.dirname(BACKEND_PATH)
  });

  backendProcess.stdout.on('data', (data) => {
    log.info(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    log.error(`[Backend Error] ${data.toString().trim()}`);
  });

  backendProcess.on('error', (error) => {
    log.error('Failed to start backend:', error);
    dialog.showErrorBox(
      'Backend Error',
      'Failed to start the JARVIS backend. Please ensure Python is installed.'
    );
  });

  backendProcess.on('close', (code) => {
    log.info(`Backend process exited with code ${code}`);
    if (!isQuitting && code !== 0) {
      // Attempt restart after delay
      setTimeout(startBackend, 5000);
    }
  });

  log.info('Backend process started');
}

function stopBackend() {
  if (backendProcess) {
    log.info('Stopping backend process...');
    
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
    } else {
      backendProcess.kill('SIGTERM');
      setTimeout(() => {
        if (!backendProcess.killed) {
          backendProcess.kill('SIGKILL');
        }
      }, 5000);
    }
    
    backendProcess = null;
  }
}

// ============== TRAY MANAGEMENT ==============

function createTray() {
  const iconPath = path.join(__dirname, 'assets/tray-icon.png');
  
  let trayIcon;
  if (fs.existsSync(iconPath)) {
    trayIcon = nativeImage.createFromPath(iconPath);
    trayIcon = trayIcon.resize({ width: 16, height: 16 });
  } else {
    // Create a simple colored square as fallback
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);
  tray.setToolTip('JARVIS Ultimate');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show JARVIS',
      click: () => {
        if (mainWindow) {
          if (mainWindow.isMinimized()) mainWindow.restore();
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: 'Toggle Mode',
      submenu: [
        {
          label: 'Text Mode',
          click: () => {
            mainWindow?.webContents.send('set-mode', 'text');
          }
        },
        {
          label: 'Speech Mode',
          click: () => {
            mainWindow?.webContents.send('set-mode', 'speech');
          }
        }
      ]
    },
    { type: 'separator' },
    {
      label: 'Settings',
      click: () => {
        mainWindow?.webContents.send('navigate', 'settings');
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });

  tray.on('double-click', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  log.info('System tray created');
}

// ============== IPC HANDLERS ==============

ipcMain.handle('app:minimize', () => {
  mainWindow?.minimize();
});

ipcMain.handle('app:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});

ipcMain.handle('app:close', () => {
  mainWindow?.close();
});

ipcMain.handle('app:isMaximized', () => {
  return mainWindow?.isMaximized() || false;
});

ipcMain.handle('app:getVersion', () => {
  return app.getVersion();
});

ipcMain.handle('shell:openExternal', async (event, url) => {
  await shell.openExternal(url);
});

ipcMain.handle('dialog:showOpen', async (event, options) => {
  const result = await dialog.showOpenDialog(mainWindow, options);
  return result;
});

ipcMain.handle('dialog:showSave', async (event, options) => {
  const result = await dialog.showSaveDialog(mainWindow, options);
  return result;
});

ipcMain.handle('store:get', (event, key, defaultValue) => {
  return store.get(key, defaultValue);
});

ipcMain.handle('store:set', (event, key, value) => {
  store.set(key, value);
});

ipcMain.handle('store:delete', (event, key) => {
  store.delete(key);
});

// System control handlers
ipcMain.handle('system:screenshot', async () => {
  // In a real implementation, this would capture the screen
  log.info('Screenshot requested');
  return { success: true, message: 'Screenshot captured' };
});

ipcMain.handle('system:execute', async (event, command) => {
  log.info(`Execute command: ${command}`);
  
  try {
    // Simple command execution (be careful with security)
    const allowedCommands = ['notepad', 'calc', 'explorer'];
    const cmd = command.toLowerCase().split(' ')[0];
    
    if (allowedCommands.includes(cmd)) {
      spawn('cmd', ['/c', 'start', cmd], { detached: true });
      return { success: true, message: `Executed: ${command}` };
    }
    
    return { success: false, message: 'Command not allowed' };
  } catch (error) {
    log.error('Execute error:', error);
    return { success: false, message: error.message };
  }
});

// ============== APP EVENTS ==============

app.whenReady().then(() => {
  log.info('JARVIS Ultimate starting...');
  
  // Start backend first
  startBackend();
  
  // Wait a moment for backend to initialize
  setTimeout(() => {
    createWindow();
    createTray();
  }, 2000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopBackend();
    app.quit();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('will-quit', () => {
  stopBackend();
});

app.on('quit', () => {
  log.info('JARVIS Ultimate shutting down');
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
    shell.openExternal(navigationUrl);
  });
});

// Auto-updater (optional)
if (!isDev) {
  const { autoUpdater } = require('electron-updater');
  
  autoUpdater.checkForUpdatesAndNotify();
  
  autoUpdater.on('update-available', () => {
    log.info('Update available');
    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Available',
      message: 'A new version of JARVIS Ultimate is available. It will be downloaded in the background.',
      buttons: ['OK']
    });
  });
  
  autoUpdater.on('update-downloaded', () => {
    log.info('Update downloaded');
    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Ready',
      message: 'Update downloaded. The application will restart to apply the update.',
      buttons: ['Restart', 'Later']
    }).then((result) => {
      if (result.response === 0) {
        autoUpdater.quitAndInstall();
      }
    });
  });
}

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Someone tried to run a second instance
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
      mainWindow.show();
    }
  });
}

log.info('Main process initialized');
