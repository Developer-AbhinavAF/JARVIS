import { motion } from 'framer-motion';
import {
  Cpu,
  HardDrive,
  Battery,
  Wifi,
  Activity,
  Thermometer,
  Clock,
  TrendingUp,
  AlertTriangle,
  LayoutDashboard,
  CheckCircle,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

export default function DashboardSection() {
  const { systemStats, isConnected } = useStore();

  const cpuHistory = [
    { time: '10:00', value: 30 },
    { time: '10:05', value: 45 },
    { time: '10:10', value: 35 },
    { time: '10:15', value: 50 },
    { time: '10:20', value: 40 },
    { time: '10:25', value: 55 },
    { time: '10:30', value: systemStats.cpu.usage || 45 },
  ];

  const memoryData = [
    { name: 'Used', value: systemStats.memory.percentage || 60, color: '#ff6ec7' },
    { name: 'Free', value: 100 - (systemStats.memory.percentage || 60), color: '#22c55e' },
  ];

  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatUptime = (seconds: number) => {
    if (!seconds) return '0h 0m';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-jarvis-text">
            <LayoutDashboard size={28} className="text-jarvis-accentPink" />
            System Dashboard
          </h1>
          <p className="mt-1 text-jarvis-textMuted">
            Real-time system monitoring and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-sm text-jarvis-textMuted">
            {isConnected ? 'Live Monitoring' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-xl p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-jarvis-accentPink/20 p-2">
                <Cpu size={20} className="text-jarvis-accentPink" />
              </div>
              <span className="text-sm text-jarvis-textMuted">CPU Usage</span>
            </div>
            <span className="text-2xl font-bold text-jarvis-text">{systemStats.cpu.usage}%</span>
          </div>
          <div className="h-16">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={cpuHistory}>
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#ff6ec7"
                  fill="#ff6ec7"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-jarvis-textMuted">
            <span>{systemStats.cpu.cores} Cores</span>
            <span className="flex items-center gap-1">
              <TrendingUp size={12} className="text-green-500" />
              Normal
            </span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-panel rounded-xl p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-jarvis-accentRed/20 p-2">
                <HardDrive size={20} className="text-jarvis-accentRed" />
              </div>
              <span className="text-sm text-jarvis-textMuted">Memory</span>
            </div>
            <span className="text-2xl font-bold text-jarvis-text">{systemStats.memory.percentage}%</span>
          </div>
          <div className="h-16">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={memoryData}
                  innerRadius={20}
                  outerRadius={30}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {memoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-jarvis-textMuted">
            <span>{formatBytes(systemStats.memory.used)} used</span>
            <span>{formatBytes(systemStats.memory.total)} total</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-panel rounded-xl p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-green-500/20 p-2">
                <Battery size={20} className="text-green-500" />
              </div>
              <span className="text-sm text-jarvis-textMuted">Battery</span>
            </div>
            <span className="text-2xl font-bold text-jarvis-text">{systemStats.battery.percentage}%</span>
          </div>
          <div className="flex h-16 items-center justify-center">
            <div className="relative h-10 w-20 rounded-lg border-2 border-jarvis-textMuted p-1">
              <div
                className="h-full rounded bg-green-500 transition-all duration-500"
                style={{ width: `${systemStats.battery.percentage}%` }}
              />
              <div className="absolute -right-3 top-1/2 h-4 w-1 -translate-y-1/2 rounded-r bg-jarvis-textMuted" />
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-jarvis-textMuted">
            <span>{systemStats.battery.isCharging ? 'Charging' : 'On battery'}</span>
            <span>~4h remaining</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass-panel rounded-xl p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-blue-500/20 p-2">
                <Clock size={20} className="text-blue-500" />
              </div>
              <span className="text-sm text-jarvis-textMuted">Uptime</span>
            </div>
            <span className="text-2xl font-bold text-jarvis-text">{formatUptime(systemStats.uptime)}</span>
          </div>
          <div className="flex h-16 items-center justify-center">
            <div className="text-center">
              <div className="text-3xl font-bold text-jarvis-accentPink">
                {Math.floor(systemStats.uptime / 3600)}
              </div>
              <div className="text-xs text-jarvis-textMuted">hours online</div>
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-jarvis-textMuted">
            <span>Started today</span>
            <span className="text-green-500">Stable</span>
          </div>
        </motion.div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-panel rounded-xl p-4"
        >
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-jarvis-text">
            <Activity size={16} className="text-jarvis-accentPink" />
            CPU History (Last 30 min)
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={cpuHistory}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ff6ec7" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ff6ec7" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#ff6ec7"
                  fill="url(#cpuGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="glass-panel rounded-xl p-4"
        >
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-jarvis-text">
            <Wifi size={16} className="text-jarvis-accentPink" />
            Network Activity
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="rounded bg-green-500/20 p-1.5">
                  <TrendingUp size={14} className="text-green-500" />
                </div>
                <span className="text-sm text-jarvis-textMuted">Download</span>
              </div>
              <span className="text-sm font-semibold text-jarvis-text">
                {systemStats.network.downloadSpeed > 0
                  ? `${formatBytes(systemStats.network.downloadSpeed)}/s`
                  : '0 B/s'}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/5">
              <div
                className="h-full rounded-full bg-green-500 transition-all duration-500"
                style={{ width: `${Math.min((systemStats.network.downloadSpeed / 1000000) * 100, 100)}%` }}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="rounded bg-blue-500/20 p-1.5">
                  <TrendingUp size={14} className="rotate-180 text-blue-500" />
                </div>
                <span className="text-sm text-jarvis-textMuted">Upload</span>
              </div>
              <span className="text-sm font-semibold text-jarvis-text">
                {systemStats.network.uploadSpeed > 0
                  ? `${formatBytes(systemStats.network.uploadSpeed)}/s`
                  : '0 B/s'}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/5">
              <div
                className="h-full rounded-full bg-blue-500 transition-all duration-500"
                style={{ width: `${Math.min((systemStats.network.uploadSpeed / 500000) * 100, 100)}%` }}
              />
            </div>

            <div className="flex items-center justify-between border-t border-white/5 pt-2">
              <span className="text-sm text-jarvis-textMuted">Latency (Ping)</span>
              <span className="text-sm font-semibold text-jarvis-text">{systemStats.network.ping} ms</span>
            </div>
          </div>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="glass-panel rounded-xl p-4"
      >
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-jarvis-text">
          <AlertTriangle size={16} className="text-yellow-500" />
          System Alerts
        </h3>
        <div className="space-y-2">
          {systemStats.memory.percentage > 85 && (
            <div className="flex items-center gap-3 rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-3">
              <AlertTriangle size={16} className="text-yellow-500" />
              <span className="text-sm text-jarvis-text">
                High memory usage detected ({systemStats.memory.percentage}%)
              </span>
            </div>
          )}
          {systemStats.cpu.usage > 90 && (
            <div className="flex items-center gap-3 rounded-lg border border-red-500/20 bg-red-500/10 p-3">
              <Thermometer size={16} className="text-red-500" />
              <span className="text-sm text-jarvis-text">
                CPU usage critically high ({systemStats.cpu.usage}%)
              </span>
            </div>
          )}
          {systemStats.battery.percentage < 20 && !systemStats.battery.isCharging && (
            <div className="flex items-center gap-3 rounded-lg border border-red-500/20 bg-red-500/10 p-3">
              <Battery size={16} className="text-red-500" />
              <span className="text-sm text-jarvis-text">
                Low battery warning ({systemStats.battery.percentage}%)
              </span>
            </div>
          )}
          {systemStats.memory.percentage <= 85 &&
            systemStats.cpu.usage <= 90 &&
            systemStats.battery.percentage >= 20 && (
              <div className="flex items-center gap-3 rounded-lg border border-green-500/20 bg-green-500/10 p-3">
                <CheckCircle size={16} className="text-green-500" />
                <span className="text-sm text-jarvis-text">All systems operating normally</span>
              </div>
            )}
        </div>
      </motion.div>
    </div>
  );
}
