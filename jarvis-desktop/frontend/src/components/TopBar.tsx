import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useStore } from '@/store/useStore';
import {
  Camera,
  Youtube,
  Activity,
  Wifi,
  Calculator,
  Laugh,
  Quote,
  Sparkles,
  Cloud,
} from 'lucide-react';
import Waveform from './Waveform';

const quickActions = [
  { label: 'Screenshot', icon: Camera, command: 'take screenshot', key: '1' },
  { label: 'YouTube', icon: Youtube, command: 'open youtube', key: '2' },
  { label: 'System', icon: Activity, command: 'system status', key: '3' },
  { label: 'Network', icon: Wifi, command: 'network status', key: '4' },
  { label: 'Calculator', icon: Calculator, command: 'calculate 15 * 23', key: '5' },
  { label: 'Joke', icon: Laugh, command: 'tell me a joke', key: '6' },
  { label: 'Quote', icon: Quote, command: 'quote', key: '7' },
  { label: 'Fact', icon: Sparkles, command: 'random fact', key: '8' },
  { label: 'Weather', icon: Cloud, command: 'weather', key: '9' },
];

export default function TopBar() {
  const { mode, toggleMode, isListening, isConnected, activeTab, setInput } = useStore();
  const [now, setNow] = useState(() => new Date());
  const isAssistant = activeTab === 'assistant';

  useEffect(() => {
    const interval = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => {
      window.clearInterval(interval);
    };
  }, []);

  const formatTime = () => {
    return now.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const formatDate = () => {
    return now.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const handleQuickAction = (command: string) => {
    // Set input and dispatch event so ChatPanel can send it
    setInput(command);
    window.dispatchEvent(new CustomEvent<string>('quick-action', { detail: command }));
  };

  return (
    <header className="flex h-12 items-center justify-between px-4 glass-panel border-b border-white/10">
      <div className="flex items-center gap-3">
        <div className="flex items-center rounded-full border border-white/10 bg-black/32 p-0.5 shadow-[0_8px_20px_rgba(0,0,0,0.24)]">
          <motion.button
            onClick={() => mode !== 'text' && toggleMode()}
            className={`rounded-full px-4 py-1.5 text-[10px] font-medium tracking-[0.12em] transition-all duration-300 ${
              mode === 'text'
                ? 'mode-text-active text-white'
                : 'text-jarvis-textMuted hover:text-jarvis-text'
            }`}
            whileHover={mode !== 'text' ? { scale: 1.02 } : {}}
            whileTap={mode !== 'text' ? { scale: 0.98 } : {}}
          >
            TEXT MODE
          </motion.button>

          <motion.button
            onClick={() => mode !== 'speech' && toggleMode()}
            className={`rounded-full px-4 py-1.5 text-[10px] font-medium tracking-[0.12em] transition-all duration-300 ${
              mode === 'speech'
                ? 'mode-speech-active text-white'
                : 'text-jarvis-textMuted hover:text-jarvis-text'
            }`}
            whileHover={mode !== 'speech' ? { scale: 1.02 } : {}}
            whileTap={mode !== 'speech' ? { scale: 0.98 } : {}}
          >
            SPEECH MODE
          </motion.button>
        </div>

        <AnimatePresence>
          {mode === 'speech' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center gap-2"
            >
              <Waveform isActive={isListening} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Quick Action Toolbar - only visible in assistant tab */}
        <AnimatePresence>
          {isAssistant && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="flex items-center gap-1 ml-2 pl-3 border-l border-white/10"
            >
              {quickActions.map((action) => {
                const Icon = action.icon;
                return (
                  <motion.button
                    key={action.label}
                    onClick={() => handleQuickAction(action.command)}
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-jarvis-textMuted hover:text-jarvis-text hover:bg-white/10 transition-colors"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    title={`${action.label} (Ctrl+${action.key})`}
                  >
                    <Icon size={14} />
                  </motion.button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex flex-1 justify-center">
        {isListening && mode === 'speech' ? (
          <motion.span
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="text-xs text-jarvis-accentPink animate-pulse"
          >
            Listening...
          </motion.span>
        ) : null}
      </div>

      <div className="flex items-center gap-3 text-right">
        <div className="flex flex-col items-end">
          <span className="text-xs font-medium text-jarvis-text">{formatTime()}</span>
          <span className="text-[10px] text-jarvis-textMuted">{formatDate()}</span>
        </div>

        <span
          className={`h-2 w-2 rounded-full border border-black/20 ${
            isConnected ? 'bg-green-400 status-online shadow-[0_0_12px_rgba(74,222,128,0.7)]' : 'bg-red-500'
          }`}
          aria-label={isConnected ? 'Live connection' : 'Connection offline'}
        />
      </div>
    </header>
  );
}
