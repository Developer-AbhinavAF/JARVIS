import { motion } from 'framer-motion';
import {
  Cpu,
  HardDrive,
  Battery,
  Wifi,
  Activity,
  Camera,
  Scan,
  FileText,
  Globe,
  Brain,
  CheckCircle,
  XCircle,
  Clock,
  MoreHorizontal,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import {
  LineChart,
  Line,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';

export default function RightPanel() {
  const { systemStats, plugins } = useStore();

  // Sample data for charts (in real app, this would come from system stats history)
  const chartData = [
    { value: 30 },
    { value: 45 },
    { value: 35 },
    { value: 50 },
    { value: 40 },
    { value: 55 },
    { value: 45 },
  ];

  const formatSpeed = (bytesPerSec: number) => {
    if (bytesPerSec === 0) return '0 B/s';
    const k = 1024;
    const sizes = ['B/s', 'KB/s', 'MB/s'];
    const i = Math.floor(Math.log(bytesPerSec) / Math.log(k));
    return parseFloat((bytesPerSec / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <motion.aside
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="w-80 glass-panel border-l border-white/10 flex flex-col overflow-y-auto"
    >
      {/* System Dashboard */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-jarvis-text flex items-center gap-2">
            <Activity size={16} className="text-jarvis-accentPink" />
            System Dashboard
          </h3>
          <button className="text-jarvis-textMuted hover:text-jarvis-text transition-colors">
            <MoreHorizontal size={16} />
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          {/* CPU */}
          <StatCard
            icon={Cpu}
            label="CPU"
            value={`${systemStats?.cpu.usage ?? 23}%`}
            chartData={chartData}
            color="#ff6ec7"
          />

          {/* RAM */}
          <StatCard
            icon={HardDrive}
            label="RAM"
            value={`${systemStats?.memory.percentage ?? 62}%`}
            chartData={chartData.map((d) => ({ value: d.value * 0.8 }))}
            color="#ff3b3b"
          />

          {/* Battery */}
          <StatCard
            icon={Battery}
            label="Battery"
            value={`${systemStats?.battery.percentage ?? 78}%`}
            subValue={systemStats?.battery.isCharging ? 'Charging' : 'Discharging'}
            chartData={chartData.map((d) => ({ value: d.value * 0.6 }))}
            color="#22c55e"
          />

          {/* Disk */}
          <StatCard
            icon={HardDrive}
            label="Disk (C:)"
            value={`${systemStats?.disk.percentage ?? 45}%`}
            chartData={chartData.map((d) => ({ value: d.value * 0.5 }))}
            color="#f59e0b"
          />
        </div>

        {/* Network & Processes */}
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div className="glass-panel rounded-xl p-3">
            <div className="flex items-center gap-2 mb-2">
              <Wifi size={14} className="text-jarvis-accentPink" />
              <span className="text-xs text-jarvis-textMuted">Network</span>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-jarvis-textMuted">↓</span>
                <span className="text-jarvis-text font-medium">
                  {formatSpeed(systemStats?.network.downloadSpeed ?? 56200000)}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-jarvis-textMuted">↑</span>
                <span className="text-jarvis-text font-medium">
                  {formatSpeed(systemStats?.network.uploadSpeed ?? 18700000)}
                </span>
              </div>
            </div>
            <div className="mt-2 h-8">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
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
          </div>

          <div className="glass-panel rounded-xl p-3">
            <div className="flex items-center gap-2 mb-2">
              <Activity size={14} className="text-jarvis-accentPink" />
              <span className="text-xs text-jarvis-textMuted">Processes</span>
            </div>
            <div className="text-2xl font-bold text-jarvis-text">
              {systemStats?.processes.count ?? 142}
            </div>
            <div className="text-xs text-jarvis-textMuted">Running</div>
            <div className="mt-2 flex -space-x-1">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="w-5 h-5 rounded-full bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentRed border-2 border-jarvis-bg"
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Plugins Panel */}
      <div className="p-4 flex-1">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-jarvis-text">Plugins</h3>
          <button className="text-xs text-jarvis-accentPink hover:text-jarvis-accentPink/80 transition-colors">
            View All
          </button>
        </div>

        <div className="space-y-2">
          {plugins.map((plugin, index) => (
            <motion.div
              key={plugin.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="glass-panel rounded-xl p-3 card-lift cursor-pointer"
            >
              <div className="flex items-start gap-3">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    plugin.status === 'ready'
                      ? 'bg-jarvis-accentPink/20'
                      : 'bg-white/5'
                  }`}
                >
                  <PluginIcon name={plugin.icon} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium text-jarvis-text truncate">
                      {plugin.name}
                    </h4>
                    <StatusBadge status={plugin.status} />
                  </div>
                  <p className="text-xs text-jarvis-textMuted mt-0.5 line-clamp-1">
                    {plugin.description}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.aside>
  );
}

interface StatCardProps {
  icon: React.ComponentType<{ size?: number | string; className?: string }>;
  label: string;
  value: string;
  subValue?: string;
  chartData: Array<{ value: number }>;
  color: string;
}

function StatCard({ icon: Icon, label, value, subValue, chartData, color }: StatCardProps) {
  return (
    <div className="glass-panel rounded-xl p-3 card-lift">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={14} className="text-jarvis-accentPink" />
          <span className="text-xs text-jarvis-textMuted">{label}</span>
        </div>
      </div>
      <div className="text-xl font-bold text-jarvis-text">{value}</div>
      {subValue && <div className="text-[10px] text-jarvis-textMuted">{subValue}</div>}
      <div className="mt-2 h-8">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function PluginIcon({ name }: { name: string }) {
  const icons: Record<string, React.ComponentType<{ size?: number | string; className?: string }>> = {
    Camera,
    Scan,
    FileText,
    Globe,
    Brain,
  };

  const Icon = icons[name] || Activity;
  return <Icon size={18} className="text-jarvis-accentPink" />;
}

function StatusBadge({ status }: { status: string }) {
  const config = {
    ready: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Ready' },
    loading: { icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-500/10', label: 'Loading' },
    error: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Error' },
    not_loaded: { icon: XCircle, color: 'text-gray-500', bg: 'bg-gray-500/10', label: 'Not Loaded' },
  };

  const { icon: Icon, color, bg, label } = config[status as keyof typeof config] || config.not_loaded;

  return (
    <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${color} ${bg}`}>
      <Icon size={10} />
      {label}
    </span>
  );
}
