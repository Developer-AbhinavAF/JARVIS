import {
  Home,
  LayoutDashboard,
  Monitor,
  Brain,
  Sparkles,
  Settings,
  HelpCircle,
  Plus,
  Terminal,
  UserRound,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { motion, AnimatePresence } from 'framer-motion';

const navItems = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'pc-control', label: 'PC Control', icon: Monitor },
  { id: 'memory', label: 'Memory Center', icon: Brain },
  { id: 'logs', label: 'System Logs', icon: Terminal },
  { id: 'assistant', label: 'Smart Assistant', icon: Sparkles },
  { id: 'plugins', label: 'Plugins', icon: Plus, badge: 'NEW' },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'help', label: 'Help & Docs', icon: HelpCircle },
];

interface SidebarProps {
  collapsed?: boolean;
}

export default function Sidebar({ collapsed = false }: SidebarProps) {
  const { activeTab, setActiveTab, isConnected } = useStore();

  if (collapsed) {
    return (
      <motion.aside
        initial={{ x: -40, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="h-full w-full flex flex-col items-center py-4 border-r border-white/5 bg-jarvis-bg"
      >
        <div className="flex h-16 items-center justify-center">
          <motion.div
            className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentBlue"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Sparkles size={22} className="text-white" />
          </motion.div>
        </div>

        <nav className="mt-6 flex flex-1 flex-col items-center gap-2.5">
          {navItems.map((item, index) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <motion.button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={item.label}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.06 + index * 0.04 }}
                whileHover={{ y: -2, scale: 1.04 }}
                whileTap={{ scale: 0.97 }}
                className={`group relative flex h-10 w-10 items-center justify-center rounded-lg transition-all ${
                  isActive
                    ? 'bg-jarvis-accentPink/15 text-jarvis-accentPink'
                    : 'text-jarvis-textMuted hover:text-jarvis-text hover:bg-white/5'
                }`}
              >
                <Icon size={18} className="transition-transform group-hover:scale-110" />
                {item.id === 'plugins' && (
                  <span className="absolute -right-1 top-0.5 h-2 w-2 rounded-full bg-jarvis-accentPink shadow-[0_0_8px_rgba(255,110,199,0.8)]" />
                )}
              </motion.button>
            );
          })}
        </nav>

        <div className="mt-4 flex justify-center">
          <div className="relative">
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-slate-200 shadow-[0_12px_30px_rgba(0,0,0,0.28)]">
              <UserRound size={17} />
            </div>
            <span
              className={`absolute bottom-0.5 right-0.5 h-2.5 w-2.5 rounded-full border-2 border-[#04070e] ${
                isConnected ? 'bg-emerald-400 shadow-[0_0_14px_rgba(74,222,128,0.65)]' : 'bg-red-500'
              }`}
            />
          </div>
        </div>
      </motion.aside>
    );
  }

  return (
    <motion.aside
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={`h-full bg-jarvis-bg border-r border-white/5 flex flex-col ${collapsed ? 'w-16' : 'w-60'}`}
    >
      {/* Logo */}
      <motion.div 
        className={`border-b border-white/5 flex items-center ${collapsed ? 'h-16 justify-center px-2' : 'h-16 px-5'}`}
        layout
        transition={{ duration: 0.3 }}
      >
        <motion.div 
          className={`rounded-xl bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentRed flex items-center justify-center font-bold text-white ${collapsed ? 'w-10 h-10 text-lg' : 'w-10 h-10 text-xl'}`}
          layout
          whileHover={{ scale: 1.05, rotate: 5 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 400, damping: 17 }}
        >
          J
        </motion.div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
              className="ml-3"
            >
              <h1 className="font-bold text-white text-lg tracking-wide">JARVIS</h1>
              <p className="text-[10px] text-jarvis-textMuted uppercase tracking-wider">Ultimate</p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Navigation */}
      <nav className={`flex-1 py-3 ${collapsed ? 'px-2 space-y-2' : 'px-3 space-y-1'}`}>
        {navItems.map((item, index) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <motion.button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05, duration: 0.3 }}
              whileHover={{ scale: 1.02, x: collapsed ? 0 : 4 }}
              whileTap={{ scale: 0.98 }}
              className={`flex items-center rounded-lg transition-colors duration-200 group relative overflow-hidden ${
                collapsed
                  ? 'w-12 h-12 justify-center mx-auto'
                  : 'w-full h-11 px-3 gap-3 text-sm font-medium'
              } ${
                isActive
                  ? 'bg-jarvis-accentPink/15 text-jarvis-accentPink'
                  : 'text-jarvis-textMuted hover:text-jarvis-text hover:bg-white/5'
              }`}
              title={item.label}
            >
              {isActive && !collapsed && (
                <motion.div
                  layoutId="activeIndicator"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-jarvis-accentPink rounded-r-full"
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                />
              )}
              <motion.div
                animate={{ rotate: isActive ? [0, -10, 10, 0] : 0 }}
                transition={{ duration: 0.5 }}
              >
                <Icon size={collapsed ? 20 : 18} className={isActive ? 'text-jarvis-accentPink' : 'group-hover:text-jarvis-text'} />
              </motion.div>
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.15 }}
                    className="whitespace-nowrap overflow-hidden"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
              {item.badge && collapsed && (
                <motion.span 
                  className="absolute top-2 right-2 w-2 h-2 rounded-full bg-jarvis-accentPink"
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
              <AnimatePresence>
                {item.badge && !collapsed && (
                  <motion.span 
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0 }}
                    className="ml-auto text-[10px] bg-jarvis-accentPink text-white px-1.5 py-0.5 rounded"
                  >
                    {item.badge}
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.button>
          );
        })}
      </nav>

      {/* User Profile */}
      <motion.div 
        className={`border-t border-white/5 ${collapsed ? 'p-2 h-16 flex items-center justify-center' : 'p-3'}`}
        layout
      >
        <div className={`flex items-center ${collapsed ? '' : 'gap-3'}`}>
          <motion.div 
            className="relative"
            whileHover={{ scale: 1.1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 17 }}
          >
            <motion.div 
              className={`rounded-full bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentRed flex items-center justify-center ${collapsed ? 'w-9 h-9' : 'w-9 h-9'}`}
              animate={isConnected ? { boxShadow: ['0 0 0 0 rgba(34, 197, 94, 0)', '0 0 0 4px rgba(34, 197, 94, 0.3)', '0 0 0 0 rgba(34, 197, 94, 0)'] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <span className="text-white font-bold text-sm">J</span>
            </motion.div>
            <motion.div
              className={`absolute -bottom-0.5 -right-0.5 rounded-full border-2 border-jarvis-bg ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              } w-2.5 h-2.5`}
              animate={isConnected ? { scale: [1, 1.2, 1] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </motion.div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div 
                className="flex-1 min-w-0"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                <p className="text-sm font-medium text-jarvis-text truncate">
                  JARVIS
                </p>
                <motion.p 
                  className="text-[10px] text-jarvis-textMuted"
                  animate={isConnected ? { opacity: [0.5, 1, 0.5] } : {}}
                  transition={{ duration: 3, repeat: Infinity }}
                >
                  {isConnected ? 'Online' : 'Offline'}
                </motion.p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </motion.aside>
  );
}
