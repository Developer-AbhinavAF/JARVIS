import {
  Crown,
  Monitor,
  Search,
  StickyNote,
  CheckSquare,
  Bell,
  Newspaper,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { motion } from 'framer-motion';

const shortcuts = [
  { id: 'features', label: 'Features Hub', icon: Crown, description: '60+ powerful features', color: 'from-yellow-500 to-amber-500' },
  { id: 'pc-control', label: 'PC Control', icon: Monitor, description: 'Manage your system' },
  { id: 'web-search', label: 'Web Search', icon: Search, description: 'Search the web' },
  { id: 'notes', label: 'Notes', icon: StickyNote, description: 'Save your thoughts' },
  { id: 'todos', label: 'To-Do List', icon: CheckSquare, description: 'Organize tasks' },
  { id: 'reminders', label: 'Reminders', icon: Bell, description: 'Never miss any' },
  { id: 'briefing', label: 'Daily Briefing', icon: Newspaper, description: 'Your day overview' },
];

interface BottomBarProps {
  collapsed?: boolean;
}

export default function BottomBar({ collapsed = false }: BottomBarProps) {
  const { addMessage, setActiveTab } = useStore();

  const handleShortcut = (id: string, label: string) => {
    if (id === 'features') {
      // Features hub will be opened via custom event
      window.dispatchEvent(new CustomEvent('open-features-hub'));
    } else if (id === 'web-search') {
      addMessage({ role: 'user', content: 'search web' });
    } else if (id === 'notes') {
      setActiveTab('memory');
    } else if (id === 'todos') {
      setActiveTab('memory');
    } else {
      addMessage({ role: 'user', content: `open ${label.toLowerCase()}` });
    }
  };

  return (
    <motion.div 
      className={`bg-jarvis-bg border-t border-white/5 flex items-center ${collapsed ? 'h-10 px-2 justify-center' : 'h-16 px-4 gap-3'}`}
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {!collapsed ? (
        <>
          {shortcuts.map((shortcut, index) => {
            const Icon = shortcut.icon;
            return (
              <motion.button
                key={shortcut.id}
                onClick={() => handleShortcut(shortcut.id, shortcut.label)}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.95 }}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors text-sm text-jarvis-textMuted hover:text-jarvis-text"
              >
                <motion.div
                  whileHover={{ rotate: 10 }}
                  transition={{ type: 'spring', stiffness: 400 }}
                >
                  <Icon size={16} className="text-jarvis-accentPink" />
                </motion.div>
                <span className="whitespace-nowrap">{shortcut.label}</span>
              </motion.button>
            );
          })}
        </>
      ) : (
        /* Collapsed view - icon row */
        <div className="flex items-center gap-2">
          {shortcuts.slice(0, 6).map((shortcut, index) => {
            const Icon = shortcut.icon;
            return (
              <motion.button
                key={shortcut.id}
                onClick={() => handleShortcut(shortcut.id, shortcut.label)}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05, type: 'spring', stiffness: 500, damping: 30 }}
                whileHover={{ scale: 1.2, y: -2 }}
                whileTap={{ scale: 0.9 }}
                className="w-8 h-8 rounded bg-white/5 hover:bg-jarvis-accentPink/20 flex items-center justify-center transition-colors"
                title={shortcut.label}
              >
                <Icon size={16} className="text-jarvis-textMuted hover:text-jarvis-accentPink" />
              </motion.button>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
