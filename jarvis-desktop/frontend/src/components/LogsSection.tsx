import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Terminal,
  Trash2,
  Download,
  Search,
  Pause,
  Play,
  Copy,
  Check,
  Braces,
  ArrowDown,
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

const FILTERS: Array<{ value: string; label: string }> = [
  { value: 'all', label: 'All Logs' },
  { value: 'chat', label: 'Chat Requests' },
  { value: 'system', label: 'System' },
  { value: 'info', label: 'INFO Level' },
  { value: 'warning', label: 'WARNING Level' },
  { value: 'error', label: 'ERROR Level' },
  { value: 'debug', label: 'DEBUG Level' },
];

const MAX_LOGS = 1000;
const EXPAND_THRESHOLD = 320;

function timeOf(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '--:--:--';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function LogsSection() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [atBottom, setAtBottom] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [bufferedCount, setBufferedCount] = useState(0);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pausedRef = useRef(false);
  const pendingRef = useRef<LogEntry[]>([]);

  const setPaused = useCallback((next: boolean) => {
    pausedRef.current = next;
    setIsPaused(next);
    if (!next && pendingRef.current.length > 0) {
      const pending = pendingRef.current;
      pendingRef.current = [];
      setLogs((prev) => [...prev, ...pending].slice(-MAX_LOGS));
      setBufferedCount(0);
      setAtBottom(true);
    }
  }, []);

  const appendLog = useCallback((entry: LogEntry) => {
    const newLog: LogEntry = { ...entry, id: entry.id || `${Date.now()}-${Math.random()}` };
    if (pausedRef.current) {
      pendingRef.current.push(newLog);
      setBufferedCount(pendingRef.current.length);
      return;
    }
    setLogs((prev) => [...prev, newLog].slice(-MAX_LOGS));
  }, []);

  // Auto-scroll to bottom (only while pinned at the bottom).
  useEffect(() => {
    if (atBottom && !isPaused && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isPaused, atBottom]);

  // Connect to WebSocket for real-time terminal logs (mount only — no
  // reconnect churn when pausing, pauses just buffer incoming entries).
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8001/ws/logs');
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'log' && data.data) {
          const backendLog: BackendLog = data.data;
          appendLog({
            id: `${Date.now()}-${Math.random()}`,
            timestamp: backendLog.timestamp,
            level: backendLog.level,
            logger: backendLog.logger,
            message: backendLog.message,
          });
        } else if (data.type === 'batch' && Array.isArray(data.logs)) {
          const batch: LogEntry[] = data.logs.map((log: BackendLog, index: number) => ({
            id: `batch-${index}`,
            timestamp: log.timestamp,
            level: log.level,
            logger: log.logger,
            message: log.message,
          }));
          if (pausedRef.current) {
            pendingRef.current = [...batch, ...pendingRef.current];
            setBufferedCount(pendingRef.current.length);
          } else {
            setLogs((prev) => [...prev, ...batch].slice(-MAX_LOGS));
          }
        }
      } catch (e) {
        // Silent fail
      }
    };

    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => setIsConnected(false);

    return () => {
      ws.close();
    };
  }, [appendLog]);

  // Also fetch initial logs via REST API
  useEffect(() => {
    fetch('http://localhost:8001/api/logs?limit=200')
      .then((res) => res.json())
      .then((data) => {
        if (data.logs && Array.isArray(data.logs)) {
          const initialLogs: LogEntry[] = data.logs.map((log: BackendLog, index: number) => ({
            id: `initial-${index}`,
            timestamp: log.timestamp,
            level: log.level,
            logger: log.logger,
            message: log.message,
          }));
          setLogs((prev) => [...initialLogs, ...prev].slice(-MAX_LOGS));
        }
      })
      .catch(() => {
        // Silent fail - WebSocket will handle live logs
      });
  }, []);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    setAtBottom(distance < 24);
  }, []);

  const clearLogs = () => {
    setLogs([]);
    pendingRef.current = [];
    setBufferedCount(0);
  };

  const copyEntry = async (entry: LogEntry) => {
    const text = `[${timeOf(entry.timestamp)}] ${entry.level}:${entry.logger}: ${entry.message}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(entry.id);
      window.setTimeout(() => setCopiedId(null), 1500);
    } catch {
      // clipboard unavailable
    }
  };

  const downloadLogs = (format: 'txt' | 'json') => {
    const date = new Date().toISOString().split('T')[0];
    let content: string;
    let type: string;
    let filename: string;
    if (format === 'json') {
      content = JSON.stringify(
        { generated_at: new Date().toISOString(), count: logs.length, logs },
        null,
        2
      );
      type = 'application/json';
      filename = `jarvis-logs-${date}.json`;
    } else {
      content = logs
        .map((log) => `[${timeOf(log.timestamp)}] ${log.level}:${log.logger}: ${log.message}`)
        .join('\n');
      type = 'text/plain';
      filename = `jarvis-logs-${date}.txt`;
    }
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredLogs = logs.filter((log) => {
    const matchesFilter =
      filter === 'all' ||
      (filter === 'error' && log.level === 'ERROR') ||
      (filter === 'warning' && log.level === 'WARNING') ||
      (filter === 'info' && log.level === 'INFO') ||
      (filter === 'debug' && log.level === 'DEBUG') ||
      (filter === 'chat' && log.message.includes('Chat request')) ||
      (filter === 'system' && log.message.includes('System'));
    if (!matchesFilter) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      log.message.toLowerCase().includes(q) ||
      log.logger.toLowerCase().includes(q) ||
      log.level.toLowerCase().includes(q) ||
      timeOf(log.timestamp).includes(q)
    );
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
    errors: logs.filter((l) => l.level === 'ERROR').length,
    warnings: logs.filter((l) => l.level === 'WARNING').length,
    info: logs.filter((l) => l.level === 'INFO').length,
  };

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
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
            <div className="text-xs text-jarvis-textMuted">Buffered</div>
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
          <div className="glass-panel rounded-lg p-3 flex items-center justify-center gap-2">
            {isPaused && bufferedCount > 0 && (
              <span className="rounded-full bg-yellow-500/20 px-2 py-0.5 text-[10px] font-medium text-yellow-400">
                {bufferedCount} buffered
              </span>
            )}
            <button
              onClick={() => setPaused(!isPaused)}
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
              placeholder="Search logs (message, logger, level, time)..."
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
            {FILTERS.map((f) => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>

          {/* Actions */}
          <button
            onClick={() => downloadLogs('json')}
            className="p-2 rounded-lg hover:bg-white/10 text-jarvis-textMuted hover:text-jarvis-text transition-colors"
            title="Download JSON"
          >
            <Braces size={18} />
          </button>
          <button
            onClick={() => downloadLogs('txt')}
            className="p-2 rounded-lg hover:bg-white/10 text-jarvis-textMuted hover:text-jarvis-text transition-colors"
            title="Download TXT"
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
      <div className="relative flex-1 overflow-hidden">
        <div
          className="h-full overflow-y-auto p-4 font-mono text-sm bg-black/40"
          onScroll={handleScroll}
        >
          {filteredLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-jarvis-textMuted">
              <Terminal size={48} className="mb-4 opacity-50" />
              <p>No logs to display</p>
              <p className="text-sm mt-1">Waiting for backend logs...</p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {filteredLogs.map((log) => {
                const isChatRequest = log.message.includes('Chat request');
                const isHttpRequest = log.message.includes('127.0.0.1') || log.message.includes('POST') || log.message.includes('HTTP');
                const isExpanded = expandedIds.has(log.id);
                const long = log.message.length > EXPAND_THRESHOLD;

                return (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={`group flex items-start gap-2 whitespace-pre-wrap break-all rounded px-1.5 py-0.5 transition-colors hover:bg-white/5 ${
                      isChatRequest ? 'text-green-400' :
                      isHttpRequest ? 'text-cyan-400' :
                      log.level === 'ERROR' ? 'text-red-400' :
                      log.level === 'WARNING' ? 'text-yellow-400' :
                      'text-gray-300'
                    }`}
                  >
                    <span className="shrink-0 text-gray-600 select-none">{timeOf(log.timestamp)}</span>
                    {long ? (
                      <button
                        onClick={() => toggleExpanded(log.id)}
                        className="text-left flex-1 min-w-0"
                        title={isExpanded ? 'Collapse' : 'Expand full entry'}
                      >
                        <span className={getLevelColor(log.level)}>{log.level}:</span>
                        <span className="text-gray-500">{log.logger}:</span>
                        <span className="text-gray-300">
                          {isExpanded ? log.message : `${log.message.slice(0, EXPAND_THRESHOLD)}…`}
                        </span>
                        {!isExpanded && <span className="text-jarvis-accentPink"> (click to expand)</span>}
                      </button>
                    ) : (
                      <span className="flex-1 min-w-0">
                        <span className={getLevelColor(log.level)}>{log.level}:</span>
                        <span className="text-gray-500">{log.logger}:</span>
                        <span className="text-gray-300">{log.message}</span>
                      </span>
                    )}
                    <button
                      onClick={() => copyEntry(log)}
                      className="shrink-0 rounded p-0.5 text-gray-600 opacity-0 transition-opacity hover:text-jarvis-accentPink group-hover:opacity-100"
                      title="Copy entry"
                    >
                      {copiedId === log.id ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                    </button>
                  </motion.div>
                );
              })}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>

        {/* Scroll to latest */}
        {!atBottom && !isPaused && (
          <motion.button
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={() => {
              setAtBottom(true);
              logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5 rounded-full bg-jarvis-accentPink/90 px-3 py-1.5 text-xs font-medium text-white shadow-lg shadow-black/40 transition-colors hover:bg-jarvis-accentPink"
          >
            <ArrowDown size={13} />
            Scroll to latest
          </motion.button>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/10 flex items-center justify-between text-xs text-jarvis-textMuted font-mono">
        <div className="flex items-center gap-4">
          <span className={isConnected ? 'text-green-400' : 'text-red-400'}>
            {isConnected ? '● Connected' : '● Disconnected'}
          </span>
          <span>Buffer: {logs.length}/{MAX_LOGS}</span>
          {isPaused && (
            <span className="text-yellow-400">
              ⏸ PAUSED{bufferedCount > 0 ? ` · ${bufferedCount} buffered` : ''}
            </span>
          )}
          {!atBottom && <span className="text-cyan-400">Auto-scroll off</span>}
        </div>
        <div className="flex items-center gap-2">
          <span>Real-time terminal logs · TXT / JSON export</span>
        </div>
      </div>
    </div>
  );
}