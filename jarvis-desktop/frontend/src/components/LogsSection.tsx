import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Terminal,
  Trash2,
  Download,
  Filter,
  Search,
  AlertCircle,
  CheckCircle,
  Info,
  X,
  Clock,
  RefreshCw,
  Cpu,
  Activity,
  MessageSquare,
  Volume2,
  Monitor,
  Power,
} from 'lucide-react';
import { useStore } from '@/store/useStore';

interface LogEntry {
  id: string;
  timestamp: number;
  level: 'info' | 'success' | 'warning' | 'error';
  category: 'system' | 'voice' | 'chat' | 'control' | 'network';
  message: string;
  details?: string;
}

export default function LogsSection() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const { systemStats } = useStore();

  // Connect to WebSocket for real-time logs
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8001/ws');
    
    ws.onopen = () => {
      setIsConnected(true);
      addLog('system', 'Connected to JARVIS', 'info');
      
      // Request initial stats
      ws.send(JSON.stringify({ type: 'get_stats' }));
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'chat_response') {
          addLog('chat', `AI: ${data.data?.response?.substring(0, 50)}...`, 'info');
        } else if (data.type === 'system_stats') {
          // Only log significant changes
          if (data.payload?.cpu?.usage > 80) {
            addLog('system', `High CPU usage: ${data.payload.cpu.usage}%`, 'warning');
          }
        }
      } catch (e) {
        // Silent fail
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      addLog('system', 'Disconnected from JARVIS', 'warning');
    };
    
    ws.onerror = () => {
      addLog('system', 'Connection error', 'error');
    };

    // Add some initial logs
    addLog('system', 'JARVIS Desktop initialized', 'info');
    addLog('voice', 'Speech recognition ready', 'success');
    
    return () => {
      ws.close();
    };
  }, []);

  const addLog = (category: LogEntry['category'], message: string, level: LogEntry['level']) => {
    const newLog: LogEntry = {
      id: Date.now().toString() + Math.random(),
      timestamp: Date.now(),
      level,
      category,
      message,
    };
    setLogs(prev => [newLog, ...prev].slice(0, 500)); // Keep last 500 logs
  };

  // Expose addLog globally for other components
  useEffect(() => {
    (window as any).jarvisLog = (category: string, message: string, level: string = 'info') => {
      addLog(category as any, message, level as any);
    };
  }, []);

  const clearLogs = () => {
    setLogs([]);
    addLog('system', 'Logs cleared', 'info');
  };

  const downloadLogs = () => {
    const logText = logs
      .map(log => `[${new Date(log.timestamp).toLocaleString()}] [${log.level.toUpperCase()}] [${log.category}] ${log.message}`)
      .join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `jarvis-logs-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    
    addLog('system', 'Logs downloaded', 'success');
  };

  const filteredLogs = logs.filter(log => {
    const matchesFilter = filter === 'all' || log.category === filter || log.level === filter;
    const matchesSearch = log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          log.category.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'system': return Cpu;
      case 'voice': return Volume2;
      case 'chat': return MessageSquare;
      case 'control': return Monitor;
      case 'network': return Activity;
      default: return Info;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'success': return 'text-green-400 bg-green-400/10 border-green-400/20';
      case 'warning': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
      case 'error': return 'text-red-400 bg-red-400/10 border-red-400/20';
      default: return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
    }
  };

  const stats = {
    total: logs.length,
    errors: logs.filter(l => l.level === 'error').length,
    warnings: logs.filter(l => l.level === 'warning').length,
    info: logs.filter(l => l.level === 'info').length,
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
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="glass-panel rounded-lg p-3">
            <div className="text-2xl font-bold text-jarvis-text">{stats.total}</div>
            <div className="text-xs text-jarvis-textMuted">Total Logs</div>
          </div>
          <div className="glass-panel rounded-lg p-3">
            <div className="text-2xl font-bold text-green-400">{stats.info}</div>
            <div className="text-xs text-jarvis-textMuted">Info</div>
          </div>
          <div className="glass-panel rounded-lg p-3">
            <div className="text-2xl font-bold text-yellow-400">{stats.warnings}</div>
            <div className="text-xs text-jarvis-textMuted">Warnings</div>
          </div>
          <div className="glass-panel rounded-lg p-3">
            <div className="text-2xl font-bold text-red-400">{stats.errors}</div>
            <div className="text-xs text-jarvis-textMuted">Errors</div>
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
            <option value="all">All Categories</option>
            <option value="system">System</option>
            <option value="voice">Voice</option>
            <option value="chat">Chat</option>
            <option value="control">Control</option>
            <option value="info">Info Level</option>
            <option value="warning">Warning Level</option>
            <option value="error">Error Level</option>
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

      {/* Logs List */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-jarvis-textMuted">
            <Terminal size={48} className="mb-4 opacity-50" />
            <p>No logs to display</p>
            <p className="text-sm mt-1">Logs will appear here as you use JARVIS</p>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence>
              {filteredLogs.map((log) => {
                const Icon = getCategoryIcon(log.category);
                return (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className={`p-3 rounded-lg border ${getLevelColor(log.level)} flex items-start gap-3`}
                  >
                    <div className="p-1.5 rounded bg-white/10">
                      <Icon size={14} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono opacity-70">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-white/10">
                          {log.category}
                        </span>
                        {log.level !== 'info' && (
                          <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-white/20">
                            {log.level}
                          </span>
                        )}
                      </div>
                      <p className="text-sm">{log.message}</p>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/10 flex items-center justify-between text-xs text-jarvis-textMuted">
        <div className="flex items-center gap-4">
          <span>Auto-refresh: ON</span>
          <span>Max entries: 500</span>
        </div>
        <div className="flex items-center gap-2">
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
          <button
            onClick={() => window.location.reload()}
            className="p-1 hover:bg-white/10 rounded"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
