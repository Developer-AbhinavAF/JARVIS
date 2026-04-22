import { motion } from 'framer-motion';
import {
  Home,
  LayoutDashboard,
  Monitor,
  Brain,
  Sparkles,
  Settings,
  HelpCircle,
  Plus,
} from 'lucide-react';
import { useStore } from '@/store/useStore';

const navItems = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'pc-control', label: 'PC Control', icon: Monitor },
  { id: 'memory', label: 'Memory Center', icon: Brain },
  { id: 'assistant', label: 'Smart Assistant', icon: Sparkles },
  { id: 'plugins', label: 'Plugins', icon: Plus, badge: 'NEW' },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'help', label: 'Help & Docs', icon: HelpCircle },
];

export default function Sidebar() {
  const { activeTab, setActiveTab, isConnected } = useStore();

  return (
    <motion.aside
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="w-60 h-full glass-panel border-r border-white/10 flex flex-col"
    >
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <h1 className="text-2xl font-bold tracking-wider">
          <span className="gradient-text">JARVIS</span>
        </h1>
        <p className="text-xs text-jarvis-textMuted uppercase tracking-widest mt-1">
          Ultimate
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <motion.button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-jarvis-accentPink/20 to-transparent text-jarvis-accentPink border-l-2 border-jarvis-accentPink'
                  : 'text-jarvis-textMuted hover:text-jarvis-text hover:bg-white/5'
              }`}
              whileHover={{ x: 4 }}
              whileTap={{ scale: 0.98 }}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.badge && (
                <span className="ml-auto text-[10px] bg-jarvis-accentPink text-white px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </motion.button>
          );
        })}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentRed flex items-center justify-center">
              <span className="text-white font-bold text-sm">J</span>
            </div>
            <div
              className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-jarvis-bg ${
                isConnected ? 'bg-green-500 status-online' : 'bg-red-500'
              }`}
            />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-jarvis-text truncate">
              JARVIS Ultimate
            </p>
            <p className="text-xs text-jarvis-textMuted flex items-center gap-1">
              <span className={isConnected ? 'text-green-500' : 'text-red-500'}>
                ●
              </span>
              {isConnected ? 'Online' : 'Offline'}
            </p>
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
