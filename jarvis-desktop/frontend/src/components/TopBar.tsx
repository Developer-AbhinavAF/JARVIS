import { motion } from 'framer-motion';
import { useStore } from '@/store/useStore';
import Waveform from './Waveform';

export default function TopBar() {
  const { mode, toggleMode, isListening, isConnected } = useStore();

  const formatTime = () => {
    const now = new Date();
    return now.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const formatDate = () => {
    const now = new Date();
    return now.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <header className="h-16 glass-panel border-b border-white/10 flex items-center justify-between px-6">
      {/* Mode Toggle */}
      <div className="flex items-center gap-4">
        <div className="flex items-center bg-black/30 rounded-full p-1 border border-white/10">
          {/* Text Mode Button */}
          <motion.button
            onClick={() => mode !== 'text' && toggleMode()}
            className={`px-6 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
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
            className={`px-6 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
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

        {/* Waveform Visualization */}
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
      </div>

      {/* Status Text */}
      <div className="flex-1 flex justify-center">
        {isListening && mode === 'speech' && (
          <motion.span
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="text-sm text-jarvis-accentPink animate-pulse"
          >
            Listening...
          </motion.span>
        )}
      </div>

      {/* Date/Time & Connection Status */}
      <div className="flex items-center gap-4 text-right">
        <div className="flex flex-col items-end">
          <span className="text-sm font-medium text-jarvis-text">{formatTime()}</span>
          <span className="text-xs text-jarvis-textMuted">{formatDate()}</span>
        </div>

        <div className="flex items-center gap-2 ml-4">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 status-online' : 'bg-red-500'
            }`}
          />
        </div>
      </div>
    </header>
  );
}
