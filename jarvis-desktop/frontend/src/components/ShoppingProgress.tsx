import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '@/store/useStore';
import { Search, ShoppingBag, CheckCircle, AlertCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function ShoppingProgress() {
  const { shoppingProgress, clearShoppingProgress } = useStore();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (shoppingProgress.active) {
      setVisible(true);
    } else {
      // Keep visible for a moment after completion
      const timer = setTimeout(() => setVisible(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [shoppingProgress.active]);

  if (!visible && !shoppingProgress.active) return null;

  const getStatusIcon = () => {
    switch (shoppingProgress.status) {
      case 'searching':
        return <Search size={18} className="text-jarvis-accentPink animate-pulse" />;
      case 'found':
        return <CheckCircle size={18} className="text-green-400" />;
      case 'completed':
        return <ShoppingBag size={18} className="text-jarvis-accentPink" />;
      case 'error':
        return <AlertCircle size={18} className="text-red-400" />;
      default:
        return <Search size={18} className="text-jarvis-accentPink" />;
    }
  };

  const getStatusText = () => {
    switch (shoppingProgress.status) {
      case 'searching':
        if (shoppingProgress.platform) {
          return `Searching ${shoppingProgress.platform}...`;
        }
        return 'Starting search...';
      case 'found':
        return `Found ${shoppingProgress.resultsCount} products on ${shoppingProgress.platform}`;
      case 'completed':
        return `Search complete! Found ${shoppingProgress.resultsCount} total products`;
      case 'error':
        return `Error: ${shoppingProgress.platform}`;
      default:
        return 'Searching...';
    }
  };

  const platforms = ['Amazon', 'Flipkart', 'Myntra', 'Meesho', 'Shopsy'];
  const currentPlatformIndex = platforms.indexOf(shoppingProgress.platform);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          className="fixed bottom-24 left-1/2 -translate-x-1/2 z-40"
        >
          <div className="glass-panel rounded-2xl px-6 py-4 min-w-[320px] border border-jarvis-accentPink/30 shadow-lg shadow-jarvis-accentPink/10">
            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
              <motion.div
                animate={{ rotate: shoppingProgress.status === 'searching' ? 360 : 0 }}
                transition={{ duration: 2, repeat: shoppingProgress.status === 'searching' ? Infinity : 0, ease: 'linear' }}
                className="w-10 h-10 rounded-xl bg-gradient-to-br from-jarvis-accentPink/20 to-jarvis-accentRed/20 flex items-center justify-center"
              >
                {getStatusIcon()}
              </motion.div>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">{shoppingProgress.query}</p>
                <p className="text-xs text-jarvis-textMuted">{getStatusText()}</p>
              </div>
              {shoppingProgress.status === 'completed' && (
                <motion.button
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  onClick={clearShoppingProgress}
                  className="p-1.5 rounded-lg hover:bg-white/10 text-jarvis-textMuted transition-colors"
                >
                  <CheckCircle size={16} className="text-green-400" />
                </motion.button>
              )}
            </div>

            {/* Platform Progress */}
            <div className="space-y-2">
              {platforms.map((platform, index) => {
                const isCurrent = platform === shoppingProgress.platform && shoppingProgress.status === 'searching';
                const isCompleted = currentPlatformIndex > index || 
                  (shoppingProgress.status === 'completed') ||
                  (shoppingProgress.status === 'found' && platforms.indexOf(shoppingProgress.platform) >= index);

                return (
                  <motion.div
                    key={platform}
                    className="flex items-center gap-3"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    {/* Status Indicator */}
                    <div className="w-5 h-5 rounded-full flex items-center justify-center">
                      {isCompleted ? (
                        <CheckCircle size={14} className="text-green-400" />
                      ) : isCurrent ? (
                        <motion.div
                          className="w-3 h-3 rounded-full bg-jarvis-accentPink"
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 1, repeat: Infinity }}
                        />
                      ) : (
                        <div className="w-2 h-2 rounded-full bg-white/20" />
                      )}
                    </div>

                    {/* Platform Name */}
                    <span className={`text-sm ${isCompleted ? 'text-jarvis-text' : isCurrent ? 'text-jarvis-accentPink' : 'text-jarvis-textMuted'}`}>
                      {platform}
                    </span>

                    {/* Animated dots for current */}
                    {isCurrent && (
                      <div className="flex gap-0.5">
                        {[0, 1, 2].map((i) => (
                          <motion.div
                            key={i}
                            className="w-1 h-1 rounded-full bg-jarvis-accentPink"
                            animate={{ opacity: [0.3, 1, 0.3] }}
                            transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.2 }}
                          />
                        ))}
                      </div>
                    )}

                    {/* Results count */}
                    {isCompleted && shoppingProgress.platform === platform && shoppingProgress.resultsCount > 0 && (
                      <span className="text-xs text-green-400 ml-auto">
                        {shoppingProgress.resultsCount} found
                      </span>
                    )}
                  </motion.div>
                );
              })}
            </div>

            {/* Progress Bar */}
            <div className="mt-4 h-1 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-jarvis-accentPink to-jarvis-accentRed rounded-full"
                initial={{ width: 0 }}
                animate={{
                  width: shoppingProgress.status === 'completed' ? '100%' : 
                         `${((currentPlatformIndex + 1) / platforms.length) * 100}%`
                }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
