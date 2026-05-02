import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useStore } from '@/store/useStore';
import Waveform from './Waveform';

export default function TopBar() {
  const { mode, toggleMode, isListening, isConnected } = useStore();
  const [now, setNow] = useState(() => new Date());

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

  return (
    <header className="flex h-16 items-center justify-between px-6 glass-panel border-b border-white/10">
      <div className="flex items-center gap-4">
        <div className="flex items-center rounded-full border border-white/10 bg-black/32 p-1 shadow-[0_16px_40px_rgba(0,0,0,0.24)]">
          <motion.button
            onClick={() => mode !== 'text' && toggleMode()}
            className={`rounded-full px-5 py-2 text-[11px] font-medium tracking-[0.12em] transition-all duration-300 ${
              mode === 'text'
                ? 'mode-text-active text-white'
                : 'text-jarvis-textMuted hover:text-jarvis-text'
            }`}
            whileHover={mode !== 'text' ? { scale: 1.02 } : {}}
            whileTap={mode !== 'text' ? { scale: 0.98 } : {}}
          >
            TEXT MODE
          </motion.button>

          {/* Speech Mode Button */}
          <motion.button
            onClick={() => mode !== 'speech' && toggleMode()}
            className={`rounded-full px-5 py-2 text-[11px] font-medium tracking-[0.12em] transition-all duration-300 ${
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
      </div>

      <div className="flex flex-1 justify-center">
        {isListening && mode === 'speech' ? (
          <motion.span
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="text-sm text-jarvis-accentPink animate-pulse"
          >
            Listening...
          </motion.span>
        ) : null}
      </div>

      <div className="flex items-center gap-3 text-right">
        <div className="flex flex-col items-end">
          <span className="text-sm font-medium text-jarvis-text">{formatTime()}</span>
          <span className="text-xs text-jarvis-textMuted">{formatDate()}</span>
        </div>

        <span
          className={`h-2.5 w-2.5 rounded-full border border-black/20 ${
            isConnected ? 'bg-green-400 status-online shadow-[0_0_12px_rgba(74,222,128,0.7)]' : 'bg-red-500'
          }`}
          aria-label={isConnected ? 'Live connection' : 'Connection offline'}
        />
      </div>
    </header>
  );
}
