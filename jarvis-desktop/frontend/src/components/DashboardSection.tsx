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

  // Historical data for charts (would be real in production)
  const cpuHistory = [
    { time: '10:00', value: 30 },
    { time: '10:05', value: 45 },
    { time: '10:10', value: 35 },
    { time: '10:15', value: 50 },
    { time: '10:20', value: 40 },
    { time: '10:25', value: 55 },
    { time: '10:30', value: systemStats?.cpu.usage || 45 },
  ];

  const memoryData = [
    { name: 'Used', value: systemStats?.memory.percentage || 60, color: '#ff6ec7' },
    { name: 'Free', value: 100 - (systemStats?.memory.percentage || 60), color: '#22c55e' },
  ];

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatUptime = (seconds: number) => {
    if (!seconds) return '0h 0m';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-jarvis-text flex items-center gap-3">
            <LayoutDashboard size={28} className="text-jarvis-accentPink" />
            System Dashboard
          </h1>
          <p className="text-jarvis-textMuted mt-1">
            Real-time system monitoring and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-sm text-jarvis-textMuted">
            {isConnected ? 'Live Monitoring' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* CPU Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-jarvis-accentPink/20">
                <Cpu size={20} className="text-jarvis-accentPink" />
              </div>
              <span className="text-sm text-jarvis-textMuted">CPU Usage</span>
            </div>
            <span className="text-2xl font-bold text-jarvis-text">
              {systemStats?.cpu.usage ?? 0}%
            </span>
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
          <div className="flex items-center justify-between mt-2 text-xs text-jarvis-textMuted">
            <span>{systemStats?.cpu.cores || 4} Cores</span>
            <span className="flex items-center gap-1">
              <TrendingUp size={12} className="text-green-500" />
              Normal
            </span>
          </div>
        </motion.div>

        {/* Memory Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-panel rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-jarvis-accentRed/20">
                <HardDrive size={20} className="text-jarvis-accentRed" />
              </div>
              <span className="text-sm text-jarvis-textMuted">Memory</span>
            </div>
            <span className="text-2xl font-bold text-jarvis-text">
              {systemStats?.memory.percentage ?? 0}%
            </span>
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
          <div className="flex items-center justify-between mt-2 text-xs text-jarvis-textMuted">
            <span>{formatBytes(systemStats?.memory.used || 0)} used</span>
            <span>{formatBytes(systemStats?.memory.total || 0)} total</span>
          </div>
        </motion.div>

        {/* Battery Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-panel rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-green-500/20">
                <Battery size={20} className="text-green-500" />
              </div>
              <span className="text-sm text-jarvis-textMuted">Battery</span>
            </div>
            <span className="text-2xl font-bold text-jarvis-text">
              {systemStats?.battery.percentage ?? 100}%
            </span>
          </div>
          <div className="flex items-center justify-center h-16">
            <div className="relative w-20 h-10 border-2 border-jarvis-textMuted rounded-lg p-1">
              <div
                className="h-full bg-green-500 rounded transition-all duration-500"
                style={{ width: `${systemStats?.battery.percentage || 100}%` }}
              />
              <div className="absolute -right-3 top-1/2 -translate-y-1/2 w-1 h-4 bg-jarvis-textMuted rounded-r" />
            </div>
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-jarvis-textMuted">
            <span>{systemStats?.battery.isCharging ? '⚡ Charging' : '🔋 On Battery'}</span>
            <span>~4h remaining</span>
          </div>
        </motion.div>

        {/* Uptime Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass-panel rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-blue-500/20">
                <Clock size={20} className="text-blue-500" />
              </div>
              <span className="text-sm text-jarvis-textMuted">Uptime</span>
            </div>
            <span className="text-2xl font-bold text-jarvis-text">
              {formatUptime(systemStats?.uptime || 0)}
            </span>
          </div>
          <div className="h-16 flex items-center justify-center">
            <div className="text-center">
              <div className="text-3xl font-bold text-jarvis-accentPink">
                {Math.floor((systemStats?.uptime || 0) / 3600)}
              </div>
              <div className="text-xs text-jarvis-textMuted">hours online</div>
            </div>
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-jarvis-textMuted">
            <span>Started today</span>
            <span className="text-green-500">Stable</span>
          </div>
        </motion.div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* CPU History Chart */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-panel rounded-xl p-4"
        >
          <h3 className="text-sm font-semibold text-jarvis-text mb-4 flex items-center gap-2">
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

        {/* Network & Processes */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="glass-panel rounded-xl p-4"
        >
          <h3 className="text-sm font-semibold text-jarvis-text mb-4 flex items-center gap-2">
            <Wifi size={16} className="text-jarvis-accentPink" />
            Network Activity
          </h3>
          <div className="space-y-4">
            {/* Download */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded bg-green-500/20">
                  <TrendingUp size={14} className="text-green-500" />
                </div>
                <span className="text-sm text-jarvis-textMuted">Download</span>
              </div>
              <span className="text-sm font-semibold text-jarvis-text">
                {(systemStats?.network.downloadSpeed || 0) > 0
                  ? formatBytes(systemStats?.network.downloadSpeed || 0) + '/s'
                  : '0 B/s'}
              </span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.min((systemStats?.network.downloadSpeed || 0) / 1000000 * 100, 100)}%` }}
              />
            </div>

            {/* Upload */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded bg-blue-500/20">
                  <TrendingUp size={14} className="text-blue-500 rotate-180" />
                </div>
                <span className="text-sm text-jarvis-textMuted">Upload</span>
              </div>
              <span className="text-sm font-semibold text-jarvis-text">
                {(systemStats?.network.uploadSpeed || 0) > 0
                  ? formatBytes(systemStats?.network.uploadSpeed || 0) + '/s'
                  : '0 B/s'}
              </span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.min((systemStats?.network.uploadSpeed || 0) / 500000 * 100, 100)}%` }}
              />
            </div>

            {/* Ping */}
            <div className="flex items-center justify-between pt-2 border-t border-white/5">
              <span className="text-sm text-jarvis-textMuted">Latency (Ping)</span>
              <span className="text-sm font-semibold text-jarvis-text">
                {systemStats?.network.ping || 0} ms
              </span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Alerts Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="glass-panel rounded-xl p-4"
      >
        <h3 className="text-sm font-semibold text-jarvis-text mb-3 flex items-center gap-2">
          <AlertTriangle size={16} className="text-yellow-500" />
          System Alerts
        </h3>
        <div className="space-y-2">
          {(systemStats?.memory.percentage || 0) > 85 && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <AlertTriangle size={16} className="text-yellow-500" />
              <span className="text-sm text-jarvis-text">High memory usage detected ({systemStats?.memory.percentage}%)</span>
            </div>
          )}
          {(systemStats?.cpu.usage || 0) > 90 && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <Thermometer size={16} className="text-red-500" />
              <span className="text-sm text-jarvis-text">CPU usage critically high ({systemStats?.cpu.usage}%)</span>
            </div>
          )}
          {(systemStats?.battery.percentage || 100) < 20 && !systemStats?.battery.isCharging && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <Battery size={16} className="text-red-500" />
              <span className="text-sm text-jarvis-text">Low battery warning ({systemStats?.battery.percentage}%)</span>
            </div>
          )}
          {(systemStats?.memory.percentage || 0) <= 85 && (systemStats?.cpu.usage || 0) <= 90 && (systemStats?.battery.percentage || 100) >= 20 && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <CheckCircle size={16} className="text-green-500" />
              <span className="text-sm text-jarvis-text">All systems operating normally</span>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
