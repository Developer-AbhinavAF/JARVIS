/**
 * JARVIS Ultimate - Electron Preload Script
 * Secure bridge between main and renderer processes
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Window controls
  window: {
    minimize: () => ipcRenderer.invoke('app:minimize'),
    maximize: () => ipcRenderer.invoke('app:maximize'),
    close: () => ipcRenderer.invoke('app:close'),
    isMaximized: () => ipcRenderer.invoke('app:isMaximized'),
  },

  // App info
  app: {
    getVersion: () => ipcRenderer.invoke('app:getVersion'),
  },

  // Shell operations
  shell: {
    openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),
  },

  // Dialogs
  dialog: {
    showOpen: (options) => ipcRenderer.invoke('dialog:showOpen', options),
    showSave: (options) => ipcRenderer.invoke('dialog:showSave', options),
  },

  // Store (settings persistence)
  store: {
    get: (key, defaultValue) => ipcRenderer.invoke('store:get', key, defaultValue),
    set: (key, value) => ipcRenderer.invoke('store:set', key, value),
    delete: (key) => ipcRenderer.invoke('store:delete', key),
  },

  // System operations
  system: {
    screenshot: () => ipcRenderer.invoke('system:screenshot'),
    execute: (command) => ipcRenderer.invoke('system:execute', command),
  },

  // Event listeners from main process
  onSetMode: (callback) => ipcRenderer.on('set-mode', (event, mode) => callback(mode)),
  onNavigate: (callback) => ipcRenderer.on('navigate', (event, page) => callback(page)),
  
  // Remove listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
});

// For TypeScript support
window.electronAPI = window.electronAPI || {};
