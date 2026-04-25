import { motion } from 'framer-motion';
import {
  Search,
  StickyNote,
  CheckSquare,
  Bell,
  Newspaper,
  ChevronRight,
  Monitor,
  Crown,
} from 'lucide-react';
import { useStore } from '@/store/useStore';

const shortcuts = [
  { id: 'features', label: 'Features Hub', icon: Crown, description: '60+ powerful features', color: 'from-yellow-500 to-amber-500' },
  { id: 'pc-control', label: 'PC Control', icon: Monitor, description: 'Manage your system' },
  { id: 'web-search', label: 'Web Search', icon: Search, description: 'Search the web' },
  { id: 'notes', label: 'Notes', icon: StickyNote, description: 'Save your thoughts' },
  { id: 'todos', label: 'To-Do List', icon: CheckSquare, description: 'Organize tasks' },
  { id: 'reminders', label: 'Reminders', icon: Bell, description: 'Never miss any' },
  { id: 'briefing', label: 'Daily Briefing', icon: Newspaper, description: 'Your day overview' },
];

export default function BottomBar() {
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
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className="h-20 glass-panel border-t border-white/10 px-6 flex items-center gap-4 overflow-x-auto"
    >
      {shortcuts.map((shortcut, index) => {
        const Icon = shortcut.icon;
        return (
          <motion.button
            key={shortcut.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + index * 0.05 }}
            onClick={() => handleShortcut(shortcut.id, shortcut.label)}
            className="flex items-center gap-3 px-4 py-3 rounded-xl glass-panel hover:bg-white/10 transition-all min-w-fit group"
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
          >
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-jarvis-accentPink/20 to-jarvis-accentRed/20 flex items-center justify-center group-hover:from-jarvis-accentPink/30 group-hover:to-jarvis-accentRed/30 transition-all">
              <Icon size={20} className="text-jarvis-accentPink" />
            </div>
            <div className="text-left">
              <p className="text-sm font-medium text-jarvis-text whitespace-nowrap">
                {shortcut.label}
              </p>
              <p className="text-xs text-jarvis-textMuted whitespace-nowrap">
                {shortcut.description}
              </p>
            </div>
          </motion.button>
        );
      })}

      {/* Scroll Indicator */}
      <motion.button
        className="w-10 h-10 rounded-xl glass-panel flex items-center justify-center ml-auto shrink-0"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <ChevronRight size={20} className="text-jarvis-textMuted" />
      </motion.button>
    </motion.div>
  );
}
