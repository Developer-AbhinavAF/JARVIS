import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '@/store/useStore';
import { BookOpen, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

export default function LearningProgress() {
  const { learningProgress, clearLearningProgress } = useStore();

  if (!learningProgress.active) return null;

  const getStatusIcon = () => {
    if (learningProgress.percent >= 100) return <CheckCircle className="w-5 h-5 text-green-400" />;
    if (learningProgress.status.includes('Error') || learningProgress.status.includes('Failed')) {
      return <AlertCircle className="w-5 h-5 text-red-400" />;
    }
    return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
  };

  const getStatusColor = () => {
    if (learningProgress.percent >= 100) return 'from-green-500/20 to-green-600/10 border-green-500/30';
    if (learningProgress.status.includes('Error')) return 'from-red-500/20 to-red-600/10 border-red-500/30';
    return 'from-blue-500/20 to-purple-600/10 border-blue-500/30';
  };

  const getProgressColor = () => {
    if (learningProgress.percent >= 100) return 'bg-green-500';
    if (learningProgress.status.includes('Error')) return 'bg-red-500';
    return 'bg-gradient-to-r from-blue-500 to-purple-500';
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -20, scale: 0.95 }}
        className={`fixed bottom-4 right-4 z-50 w-80 bg-gradient-to-br ${getStatusColor()} backdrop-blur-xl rounded-xl border shadow-2xl overflow-hidden`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-blue-400" />
            <span className="text-sm font-semibold text-white">Learning...</span>
          </div>
          {learningProgress.percent >= 100 && (
            <button
              onClick={clearLearningProgress}
              className="p-1 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          {/* Title */}
          <p className="text-sm text-gray-300 line-clamp-2" title={learningProgress.title}>
            {learningProgress.title || 'Processing video...'}
          </p>

          {/* Progress Bar */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">{learningProgress.status || 'Processing...'}</span>
              <span className="text-white font-medium">{Math.round(learningProgress.percent)}%</span>
            </div>
            <div className="h-2 bg-gray-700/50 rounded-full overflow-hidden">
              <motion.div
                className={`h-full ${getProgressColor()} rounded-full`}
                initial={{ width: 0 }}
                animate={{ width: `${learningProgress.percent}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </div>

          {/* Status Icon & Message */}
          <div className="flex items-center gap-2 text-xs">
            {getStatusIcon()}
            <span className={learningProgress.percent >= 100 ? 'text-green-400' : 'text-blue-400'}>
              {learningProgress.percent >= 100 
                ? 'Learning complete! Ask me about the video.' 
                : learningProgress.status || 'Downloading & analyzing...'}
            </span>
          </div>

          {/* Logs */}
          {learningProgress.logs.length > 0 && (
            <div className="mt-2 p-2 bg-black/30 rounded-lg max-h-24 overflow-y-auto text-xs font-mono">
              {learningProgress.logs.slice(-3).map((log, i) => (
                <div key={i} className="text-gray-500">{log}</div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
