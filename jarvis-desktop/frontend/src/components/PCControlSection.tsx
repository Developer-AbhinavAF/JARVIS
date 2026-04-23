import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Power,
  Volume2,
  VolumeX,
  Monitor,
  Moon,
  Sun,
  Wifi,
  Bluetooth,
  BluetoothConnected,
  Lock,
  LogOut,
  RotateCcw,
  Volume1,
  Volume,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Mic,
  Camera,
  Speaker,
  Maximize,
  Minimize,
  Terminal,
  Activity,
  Trash2,
} from 'lucide-react';
import { useStore } from '@/store/useStore';

interface ControlButton {
  id: string;
  label: string;
  icon: React.ElementType;
  action: string;
  color?: string;
  description?: string;
}

const controlGroups = [
  {
    title: 'System Power',
    controls: [
      { id: 'shutdown', label: 'Shutdown', icon: Power, action: 'shutdown', color: 'text-red-500', description: 'Power off computer' },
      { id: 'restart', label: 'Restart', icon: RotateCcw, action: 'restart', color: 'text-yellow-500', description: 'Restart computer' },
      { id: 'sleep', label: 'Sleep', icon: Moon, action: 'sleep', color: 'text-blue-500', description: 'Enter sleep mode' },
      { id: 'lock', label: 'Lock', icon: Lock, action: 'lock', color: 'text-jarvis-accentPink', description: 'Lock screen' },
      { id: 'logout', label: 'Logout', icon: LogOut, action: 'logout', color: 'text-orange-500', description: 'Sign out user' },
    ] as ControlButton[],
  },
  {
    title: 'Volume & Audio',
    controls: [
      { id: 'mute', label: 'Mute', icon: VolumeX, action: 'mute', description: 'Mute all audio' },
      { id: 'unmute', label: 'Unmute', icon: Volume2, action: 'unmute', description: 'Unmute audio' },
      { id: 'volume_up', label: 'Volume +', icon: Volume2, action: 'volume_up', color: 'text-green-500', description: 'Increase volume' },
      { id: 'volume_down', label: 'Volume -', icon: Volume1, action: 'volume_down', color: 'text-yellow-500', description: 'Decrease volume' },
      { id: 'volume_max', label: 'Max', icon: Speaker, action: 'volume_max', color: 'text-red-500', description: 'Maximum volume' },
    ] as ControlButton[],
  },
  {
    title: 'Display & Brightness',
    controls: [
      { id: 'brightness_up', label: 'Brighter', icon: Sun, action: 'brightness_up', color: 'text-yellow-400', description: 'Increase brightness' },
      { id: 'brightness_down', label: 'Dimmer', icon: Moon, action: 'brightness_down', color: 'text-blue-400', description: 'Decrease brightness' },
      { id: 'night_mode', label: 'Night Mode', icon: Moon, action: 'night_mode', color: 'text-purple-400', description: 'Toggle night light' },
    ] as ControlButton[],
  },
  {
    title: 'Connectivity',
    controls: [
      { id: 'wifi_toggle', label: 'WiFi', icon: Wifi, action: 'wifi_toggle', color: 'text-blue-500', description: 'Toggle WiFi' },
      { id: 'bluetooth_toggle', label: 'Bluetooth', icon: Bluetooth, action: 'bluetooth_toggle', color: 'text-blue-400', description: 'Toggle Bluetooth' },
    ] as ControlButton[],
  },
  {
    title: 'Media Controls',
    controls: [
      { id: 'play_pause', label: 'Play/Pause', icon: Play, action: 'play_pause', description: 'Play or pause media' },
      { id: 'next_track', label: 'Next', icon: SkipForward, action: 'next_track', description: 'Next track' },
      { id: 'prev_track', label: 'Previous', icon: SkipBack, action: 'prev_track', description: 'Previous track' },
    ] as ControlButton[],
  },
  {
    title: 'System Actions',
    controls: [
      { id: 'screenshot', label: 'Screenshot', icon: Camera, action: 'screenshot', color: 'text-jarvis-accentPink', description: 'Capture screen' },
      { id: 'empty_recycle', label: 'Empty Bin', icon: Trash2, action: 'empty_recycle', color: 'text-red-400', description: 'Empty recycle bin' },
      { id: 'task_manager', label: 'Task Manager', icon: Activity, action: 'task_manager', color: 'text-green-500', description: 'Open task manager' },
      { id: 'terminal', label: 'Terminal', icon: Terminal, action: 'terminal', color: 'text-gray-400', description: 'Open terminal' },
    ] as ControlButton[],
  },
];

export default function PCControlSection() {
  const { isConnected } = useStore();
  const [executing, setExecuting] = useState<string | null>(null);
  const [logs, setLogs] = useState<Array<{ time: string; action: string; status: string }>>([]);

  const executeCommand = async (control: ControlButton) => {
    if (!isConnected) {
      addLog(control.label, 'Failed - Not connected');
      return;
    }

    setExecuting(control.id);
    addLog(control.label, 'Executing...');

    try {
      const response = await fetch('http://localhost:8001/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: control.action }),
      });

      const data = await response.json();

      if (data.success) {
        addLog(control.label, 'Success');
      } else {
        addLog(control.label, `Failed - ${data.result}`);
      }
    } catch (error) {
      addLog(control.label, 'Failed - Network error');
      // Fallback: Try to execute via chat endpoint
      try {
        await fetch('http://localhost:8001/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: control.action, session_id: 'pc-control' }),
        });
        addLog(control.label, 'Success (fallback)');
      } catch {
        // Silent fail
      }
    }

    setExecuting(null);
  };

  const addLog = (action: string, status: string) => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLogs(prev => [{ time, action, status }, ...prev].slice(0, 10));
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-jarvis-text flex items-center gap-3">
            <Monitor size={28} className="text-jarvis-accentPink" />
            PC Control Center
          </h1>
          <p className="text-jarvis-textMuted mt-1">
            Direct system control and automation commands
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg glass-panel">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-sm text-jarvis-textMuted">
            {isConnected ? 'System Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Control Groups */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
          {controlGroups.map((group, groupIndex) => (
            <motion.div
              key={group.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: groupIndex * 0.1 }}
              className="glass-panel rounded-xl p-4"
            >
              <h3 className="text-sm font-semibold text-jarvis-text mb-3 flex items-center gap-2">
                <div className="w-1 h-4 bg-jarvis-accentPink rounded-full" />
                {group.title}
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {group.controls.map((control) => {
                  const Icon = control.icon;
                  const isExecuting = executing === control.id;

                  return (
                    <motion.button
                      key={control.id}
                      onClick={() => executeCommand(control)}
                      disabled={isExecuting}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="flex flex-col items-center gap-2 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-all disabled:opacity-50 group"
                    >
                      <div className={`p-2 rounded-lg bg-white/5 group-hover:bg-white/10 transition-colors ${control.color || ''}`}>
                        <Icon size={20} />
                      </div>
                      <div className="text-center">
                        <div className="text-xs font-medium text-jarvis-text">{control.label}</div>
                        <div className="text-[10px] text-jarvis-textMuted">{control.description}</div>
                      </div>
                      {isExecuting && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-lg">
                          <div className="w-4 h-4 border-2 border-jarvis-accentPink border-t-transparent rounded-full animate-spin" />
                        </div>
                      )}
                    </motion.button>
                  );
                })}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Activity Log */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-panel rounded-xl p-4"
        >
          <h3 className="text-sm font-semibold text-jarvis-text mb-3 flex items-center gap-2">
            <Terminal size={16} className="text-jarvis-accentPink" />
            Activity Log
          </h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {logs.length === 0 ? (
              <div className="text-center py-8 text-jarvis-textMuted text-sm">
                No commands executed yet
              </div>
            ) : (
              logs.map((log, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-2 rounded-lg bg-white/5 text-xs"
                >
                  <span className="text-jarvis-textMuted font-mono">{log.time}</span>
                  <span className="text-jarvis-text flex-1">{log.action}</span>
                  <span className={`px-2 py-0.5 rounded-full ${
                    log.status.includes('Success') ? 'bg-green-500/20 text-green-400' :
                    log.status.includes('Failed') ? 'bg-red-500/20 text-red-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {log.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </motion.div>
      </div>

      {/* Quick Actions Bar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="mt-6 glass-panel rounded-xl p-4"
      >
        <h3 className="text-sm font-semibold text-jarvis-text mb-3">Quick Actions</h3>
        <div className="flex flex-wrap gap-2">
          {['open chrome', 'open notepad', 'open calculator', 'system status', 'take screenshot'].map((action) => (
            <button
              key={action}
              onClick={async () => {
                try {
                  await fetch('http://localhost:8001/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: action, session_id: 'pc-control' }),
                  });
                  addLog(action, 'Success');
                } catch {
                  addLog(action, 'Failed');
                }
              }}
              className="px-4 py-2 rounded-lg bg-jarvis-accentPink/20 text-jarvis-accentPink text-sm hover:bg-jarvis-accentPink/30 transition-colors"
            >
              {action}
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
