import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  Terminal,
  Trash2,
  Download,
  Search,
  Pause,
  Play,
} from 'lucide-react';

// Backend log format from terminal
interface BackendLog {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  raw_message?: string;
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  logger: string;
  message: string;
}

export default function LogsSection() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (!isPaused && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isPaused]);

  // Connect to WebSocket for real-time terminal logs
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8001/ws/logs');
    wsRef.current = ws;
    
    ws.onopen = () => {
      setIsConnected(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'log' && data.data) {
          const backendLog: BackendLog = data.data;
          const newLog: LogEntry = {
            id: Date.now().toString() + Math.random(),
            timestamp: backendLog.timestamp,
            level: backendLog.level,
            logger: backendLog.logger,
            message: backendLog.message,
          };
          
          if (!isPaused) {
            setLogs(prev => [...prev, newLog].slice(-1000)); // Keep last 1000 logs
          }
        }
      } catch (e) {
        // Silent fail
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
    };
    
    ws.onerror = () => {
      setIsConnected(false);
    };
    
    return () => {
      ws.close();
    };
  }, [isPaused]);

  // Also fetch initial logs via REST API
  useEffect(() => {
    fetch('http://localhost:8001/api/logs?limit=200')
      .then(res => res.json())
      .then(data => {
        if (data.logs && Array.isArray(data.logs)) {
          const initialLogs: LogEntry[] = data.logs.map((log: BackendLog, index: number) => ({
            id: `initial-${index}`,
            timestamp: log.timestamp,
            level: log.level,
            logger: log.logger,
            message: log.message,
          }));
          setLogs(prev => [...initialLogs, ...prev].slice(-1000));
        }
      })
      .catch(() => {
        // Silent fail - WebSocket will handle live logs
      });
  }, []);

  const clearLogs = () => {
    setLogs([]);
  };

  const downloadLogs = () => {
    const logText = logs
      .map(log => `${log.message}`)
      .join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `jarvis-logs-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredLogs = logs.filter(log => {
    const matchesFilter = filter === 'all' || 
                          (filter === 'error' && log.level === 'ERROR') ||
                          (filter === 'warning' && log.level === 'WARNING') ||
                          (filter === 'info' && log.level === 'INFO') ||
                          (filter === 'chat' && log.message.includes('Chat request')) ||
                          (filter === 'system' && log.message.includes('System'));
    const matchesSearch = log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          log.logger.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // Terminal color coding for log levels
  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-400';
      case 'WARNING': return 'text-yellow-400';
      case 'INFO': return 'text-green-400';
      case 'DEBUG': return 'text-blue-400';
      default: return 'text-gray-400';
    }
  };

  const stats = {
    total: logs.length,
    errors: logs.filter(l => l.level === 'ERROR').length,
    warnings: logs.filter(l => l.level === 'WARNING').length,
    info: logs.filter(l => l.level === 'INFO').length,
  };

  return (
    <div className="h-full overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-jarvis-text flex items-center gap-3">
            <Terminal size={28} className="text-jarvis-accentPink" />
            System Logs
          </h1>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-sm text-jarvis-textMuted">
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-5 gap-3 mb-4">
          <div className="glass-panel rounded-lg p-3">
            <div className="text-2xl font-bold text-jarvis-text">{stats.total}</div>
            <div className="text-xs text-jarvis-textMuted">Total</div>
          </div>
          <div className="glass-panel rounded-lg p-3">
            <div className="text-2xl font-bold text-green-400">{stats.info}</div>
            <div className="text-xs text-jarvis-textMuted">INFO</div>
          </div>
          <div className="glass-panel rounded-lg p-3">
            <div className="text-2xl font-bold text-yellow-400">{stats.warnings}</div>
            <div className="text-xs text-jarvis-textMuted">WARNING</div>
          </div>
          <div className="glass-panel rounded-lg p-3">
            <div className="text-2xl font-bold text-red-400">{stats.errors}</div>
            <div className="text-xs text-jarvis-textMuted">ERROR</div>
          </div>
          <div className="glass-panel rounded-lg p-3 flex items-center justify-center">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`p-2 rounded-lg transition-colors ${isPaused ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}
              title={isPaused ? 'Resume' : 'Pause'}
            >
              {isPaused ? <Play size={18} /> : <Pause size={18} />}
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-textMuted" />
            <input
              type="text"
              placeholder="Search logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-jarvis-text placeholder-jarvis-textMuted focus:outline-none focus:border-jarvis-accentPink"
            />
          </div>

          {/* Filter */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-jarvis-text focus:outline-none focus:border-jarvis-accentPink"
          >
            <option value="all">All Logs</option>
            <option value="chat">Chat Requests</option>
            <option value="system">System</option>
            <option value="info">INFO Level</option>
            <option value="warning">WARNING Level</option>
            <option value="error">ERROR Level</option>
          </select>

          {/* Actions */}
          <button
            onClick={downloadLogs}
            className="p-2 rounded-lg hover:bg-white/10 text-jarvis-textMuted hover:text-jarvis-text transition-colors"
            title="Download Logs"
          >
            <Download size={18} />
          </button>
          <button
            onClick={clearLogs}
            className="p-2 rounded-lg hover:bg-red-500/20 text-jarvis-textMuted hover:text-red-400 transition-colors"
            title="Clear Logs"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      {/* Terminal Logs Display */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm bg-black/40">
        {filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-jarvis-textMuted">
            <Terminal size={48} className="mb-4 opacity-50" />
            <p>No logs to display</p>
            <p className="text-sm mt-1">Waiting for backend logs...</p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {filteredLogs.map((log) => {
              // Format like terminal: INFO:__main__:Chat request: message='...'
              const isChatRequest = log.message.includes('Chat request');
              const isHttpRequest = log.message.includes('127.0.0.1') || log.message.includes('POST') || log.message.includes('HTTP');
              
              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={`whitespace-pre-wrap break-all ${
                    isChatRequest ? 'text-green-400' : 
                    isHttpRequest ? 'text-cyan-400' :
                    log.level === 'ERROR' ? 'text-red-400' :
                    log.level === 'WARNING' ? 'text-yellow-400' :
                    'text-gray-300'
                  }`}
                  style={{ fontFamily: 'Consolas, Monaco, "Courier New", monospace' }}
                >
                  {/* Terminal format like: INFO:__main__:Chat request: message='...' */}
                  {isHttpRequest ? (
                    // Indent HTTP request logs
                    <span className="pl-0">{log.message}</span>
                  ) : (
                    // Standard log format
                    <span>
                      <span className={getLevelColor(log.level)}>{log.level}:</span>
                      <span className="text-gray-500">{log.logger}:</span>
                      <span className="text-gray-300">{log.message}</span>
                    </span>
                  )}
                </motion.div>
              );
            })}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/10 flex items-center justify-between text-xs text-jarvis-textMuted font-mono">
        <div className="flex items-center gap-4">
          <span className={isConnected ? 'text-green-400' : 'text-red-400'}>
            {isConnected ? '● Connected' : '● Disconnected'}
          </span>
          <span>Buffer: {logs.length}/1000</span>
          {isPaused && <span className="text-yellow-400">⏸ PAUSED</span>}
        </div>
        <div className="flex items-center gap-2">
          <span>Real-time terminal logs</span>
        </div>
      </div>
    </div>
  );
}
