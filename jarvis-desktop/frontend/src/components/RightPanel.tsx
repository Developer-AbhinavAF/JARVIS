import {
  Activity,
  Cpu,
  HardDrive,
  Battery,
  Wifi,
  Plus,
  Camera,
  Scan,
  FileText,
  Globe,
  Brain,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { motion, AnimatePresence } from 'framer-motion';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface RightPanelProps {
  collapsed?: boolean;
}

export default function RightPanel({ collapsed = false }: RightPanelProps) {
  const { systemStats, plugins } = useStore();

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
    return `${parseFloat((bytesPerSec / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return (
    <motion.aside
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={`flex h-full flex-col overflow-hidden border-l border-white/5 bg-jarvis-bg ${collapsed ? 'w-16' : 'w-72'}`}
    >
      <motion.div
        className={`flex items-center border-b border-white/5 ${collapsed ? 'h-16 justify-center px-2' : 'h-16 px-4'}`}
        layout
      >
        <motion.div
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        >
          <Activity size={collapsed ? 22 : 18} className="text-jarvis-accentPink" />
        </motion.div>
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              className="ml-2 text-sm font-semibold text-white"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.2 }}
            >
              Dashboard
            </motion.span>
          )}
        </AnimatePresence>
      </motion.div>

      <div className="flex-1 overflow-y-auto">
        {!collapsed ? (
          <motion.div
            className="space-y-3 p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            <div className="grid grid-cols-2 gap-3">
              <StatCard
                icon={Cpu}
                label="CPU"
                value={`${systemStats.cpu.usage}%`}
                chartData={chartData}
                color="#ff6ec7"
                delay={0}
              />
              <StatCard
                icon={HardDrive}
                label="RAM"
                value={`${systemStats.memory.percentage}%`}
                chartData={chartData.map((d) => ({ value: d.value * 0.8 }))}
                color="#ff3b3b"
                delay={0.1}
              />
              <StatCard
                icon={Battery}
                label="Battery"
                value={`${systemStats.battery.percentage}%`}
                subValue={systemStats.battery.isCharging ? 'Charging' : 'Discharging'}
                chartData={chartData.map((d) => ({ value: d.value * 0.6 }))}
                color="#22c55e"
                delay={0.2}
              />
              <StatCard
                icon={HardDrive}
                label="Disk (C:)"
                value={`${systemStats.disk.percentage}%`}
                chartData={chartData.map((d) => ({ value: d.value * 0.5 }))}
                color="#f59e0b"
                delay={0.3}
              />
            </div>

            <motion.div
              className="grid grid-cols-2 gap-3"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <div className="rounded-lg bg-white/5 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <Wifi size={14} className="text-jarvis-accentPink" />
                  <span className="text-xs text-jarvis-textMuted">Network</span>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-jarvis-textMuted">DL</span>
                    <span className="font-medium text-jarvis-text">
                      {formatSpeed(systemStats.network.downloadSpeed)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-jarvis-textMuted">UL</span>
                    <span className="font-medium text-jarvis-text">
                      {formatSpeed(systemStats.network.uploadSpeed)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="rounded-lg bg-white/5 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <Activity size={14} className="text-jarvis-accentPink" />
                  <span className="text-xs text-jarvis-textMuted">Processes</span>
                </div>
                <div className="text-xl font-bold text-jarvis-text">{systemStats.processes.count}</div>
                <div className="text-[10px] text-jarvis-textMuted">Running</div>
              </div>
            </motion.div>

            <motion.div
              className="pt-2"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-jarvis-text">Plugins</h3>
                <motion.button
                  className="text-xs text-jarvis-accentPink transition-colors hover:text-jarvis-accentPink/80"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  View All
                </motion.button>
              </div>
              <div className="space-y-2">
                {plugins.map((plugin, index) => (
                  <motion.div
                    key={plugin.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    whileHover={{ scale: 1.02, x: -2 }}
                    className="cursor-pointer rounded-lg bg-white/5 p-3 transition-colors hover:bg-white/10"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${
                          plugin.status === 'ready' ? 'bg-jarvis-accentPink/20' : 'bg-white/5'
                        }`}
                      >
                        <PluginIcon name={plugin.icon} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <h4 className="truncate text-sm font-medium text-jarvis-text">{plugin.name}</h4>
                          <StatusBadge status={plugin.status} />
                        </div>
                        <p className="mt-0.5 line-clamp-1 text-xs text-jarvis-textMuted">
                          {plugin.description}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        ) : (
          <motion.div
            className="flex flex-col items-center space-y-3 py-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {[
              { icon: Cpu, color: 'text-jarvis-accentPink', bg: 'bg-jarvis-accentPink/15', title: `CPU ${systemStats.cpu.usage}%` },
              { icon: HardDrive, color: 'text-red-400', bg: 'bg-red-500/15', title: `RAM ${systemStats.memory.percentage}%` },
              { icon: Battery, color: 'text-green-400', bg: 'bg-green-500/15', title: `Battery ${systemStats.battery.percentage}%` },
              { icon: HardDrive, color: 'text-yellow-400', bg: 'bg-yellow-500/15', title: `Disk ${systemStats.disk.percentage}%` },
              { icon: Plus, color: 'text-jarvis-accentPink', bg: 'bg-jarvis-accentPink/15', title: 'Plugins' },
            ].map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1, type: 'spring', stiffness: 500, damping: 30 }}
                whileHover={{ scale: 1.15, rotate: 5 }}
                className={`flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg ${item.bg}`}
                title={item.title}
              >
                <item.icon size={20} className={item.color} />
              </motion.div>
            ))}
          </motion.div>
        )}
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
  delay?: number;
}

function StatCard({ icon: Icon, label, value, subValue, chartData, color, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      className="rounded-lg bg-white/5 p-3 transition-colors hover:bg-white/10"
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay, duration: 0.3, type: 'spring', stiffness: 200 }}
      whileHover={{ scale: 1.03, y: -2 }}
    >
      <div className="mb-2 flex items-center gap-2">
        <motion.div
          animate={{ rotate: [0, 10, -10, 0] }}
          transition={{ delay: delay + 0.5, duration: 0.5 }}
        >
          <Icon size={14} className="text-jarvis-accentPink" />
        </motion.div>
        <span className="text-xs text-jarvis-textMuted">{label}</span>
      </div>
      <motion.div
        className="text-xl font-bold text-jarvis-text"
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: delay + 0.1 }}
      >
        {value}
      </motion.div>
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
              animationDuration={1500}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

function PluginIcon({ name, size = 18 }: { name: string; size?: number }) {
  const icons: Record<string, React.ComponentType<{ size?: number | string; className?: string }>> = {
    Camera,
    Scan,
    FileText,
    Globe,
    Brain,
  };

  const Icon = icons[name] || Activity;
  return <Icon size={size} className="text-jarvis-accentPink" />;
}

function StatusBadge({ status, small = false }: { status: string; small?: boolean }) {
  const config = {
    ready: { color: 'bg-green-500', label: 'Ready' },
    loading: { color: 'bg-yellow-500', label: 'Loading' },
    error: { color: 'bg-red-500', label: 'Error' },
    not_loaded: { color: 'bg-gray-500', label: 'Not Loaded' },
  };

  const { color, label } = config[status as keyof typeof config] || config.not_loaded;

  if (small) {
    return <span className={`h-2 w-2 rounded-full ${color}`} title={label} />;
  }

  return <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-jarvis-textMuted">{label}</span>;
}
