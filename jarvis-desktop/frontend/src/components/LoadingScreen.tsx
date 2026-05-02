import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

interface LoadingScreenProps {
  onLoadingComplete: () => void;
}

export default function LoadingScreen({ onLoadingComplete }: LoadingScreenProps) {
  const [progress, setProgress] = useState(0);
  const [loadingText, setLoadingText] = useState('Initializing');

  const loadingTexts = [
    'Initializing systems',
    'Loading neural networks',
    'Calibrating sensors',
    'Establishing connection',
    'Syncing protocols',
    'Optimizing performance',
    'Ready',
  ];

  useEffect(() => {
    let completionTimeout: number | null = null;

    // Slower, more cinematic loading - ~5 seconds total
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          if (completionTimeout === null) {
            completionTimeout = window.setTimeout(onLoadingComplete, 800);
          }
          return 100;
        }
        // Variable speed - slower at start and end, faster in middle
        const increment = prev < 20 ? 1 : prev > 80 ? 0.5 : 1.5;
        return Math.min(100, prev + increment);
      });
    }, 80); // Slower interval

    return () => {
      clearInterval(interval);
      if (completionTimeout !== null) {
        window.clearTimeout(completionTimeout);
      }
    };
  }, [onLoadingComplete]);

  useEffect(() => {
    const textIndex = Math.floor((progress / 100) * (loadingTexts.length - 1));
    setLoadingText(loadingTexts[textIndex]);
  }, [progress]);

  return (
    <motion.div
      className="fixed inset-0 z-50 bg-jarvis-bg flex flex-col items-center justify-center overflow-hidden"
      initial={{ opacity: 1 }}
      exit={{ 
        opacity: 0,
        scale: 1.1,
        filter: 'blur(20px)',
      }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Animated Background Grid */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-jarvis-accentPink/5 via-transparent to-transparent" />
        
        {/* Floating particles */}
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-jarvis-accentPink/30 rounded-full"
            initial={{ 
              x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1000),
              y: Math.random() * (typeof window !== 'undefined' ? window.innerHeight : 1000),
              opacity: 0,
            }}
            animate={{ 
              y: [null, -100],
              opacity: [0, 1, 0],
            }}
            transition={{ 
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              delay: Math.random() * 2,
              ease: 'easeOut',
            }}
          />
        ))}

        {/* Grid lines */}
        <svg className="absolute inset-0 w-full h-full opacity-10">
          <defs>
            <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#ff6ec7" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center">
        {/* Logo Ring Animation */}
        <div className="relative mb-8">
          {/* Outer rings */}
          {[...Array(3)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute inset-0 rounded-full border border-jarvis-accentPink/20"
              style={{ 
                width: 140 + i * 30, 
                height: 140 + i * 30,
                left: -(20 + i * 15),
                top: -(20 + i * 15),
              }}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ 
                opacity: [0.1, 0.3, 0.1],
                scale: [1, 1.1, 1],
                rotate: [0, 180, 360],
              }}
              transition={{ 
                duration: 6 + i * 1, // Slower rotation
                repeat: Infinity,
                ease: 'linear',
              }}
            />
          ))}

          {/* Rotating gradient ring */}
          <motion.div
            className="absolute -inset-4 rounded-full"
            style={{
              background: 'conic-gradient(from 0deg, transparent, #ff6ec7, transparent, #ff3b3b, transparent)',
              filter: 'blur(8px)',
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
          />

          {/* Main Logo Container */}
          <motion.div
            className="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentRed flex items-center justify-center"
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ 
              type: 'spring',
              stiffness: 200,
              damping: 20,
              delay: 0.2,
            }}
          >
            {/* Pulse effect */}
            <motion.div
              className="absolute inset-0 rounded-2xl bg-gradient-to-br from-jarvis-accentPink to-jarvis-accentRed"
              animate={{ 
                scale: [1, 1.2, 1],
                opacity: [0.5, 0, 0.5],
              }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            />

            {/* J Letter */}
            <motion.span
              className="relative text-5xl font-bold text-white"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.5 }}
            >
              J
            </motion.span>
          </motion.div>
        </div>

        {/* JARVIS Text */}
        <motion.div
          className="mb-6 text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <motion.h1
            className="text-4xl font-bold text-white tracking-wider"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
          >
            {'JARVIS'.split('').map((char, i) => (
              <motion.span
                key={i}
                className="inline-block"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 + i * 0.05 }}
                whileHover={{ 
                  scale: 1.2,
                  color: '#ff6ec7',
                  transition: { duration: 0.2 }
                }}
              >
                {char}
              </motion.span>
            ))}
          </motion.h1>
          <motion.p
            className="text-jarvis-textMuted text-sm mt-1 tracking-[0.3em] uppercase"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.1 }}
          >
            Ultimate AI Assistant
          </motion.p>
        </motion.div>

        {/* Sound Wave Animation */}
        <div className="flex items-center gap-1 mb-8 h-12">
          {[...Array(20)].map((_, i) => (
            <motion.div
              key={i}
              className="w-1 bg-gradient-to-t from-jarvis-accentPink to-jarvis-accentRed rounded-full"
              initial={{ height: 4 }}
              animate={{ 
                height: [4, 20 + Math.random() * 30, 4],
              }}
              transition={{ 
                duration: 0.5 + Math.random() * 0.5,
                repeat: Infinity,
                delay: i * 0.05,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>

        {/* Progress Bar */}
        <div className="w-64 mb-4">
          <div className="h-1 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-jarvis-accentPink to-jarvis-accentRed rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.1 }}
            />
          </div>
        </div>

        {/* Loading Text */}
        <motion.p
          className="text-jarvis-textMuted text-sm font-mono"
          key={loadingText}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
        >
          <span className="text-jarvis-accentPink">{'>'}</span> {loadingText}...
          <motion.span
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 0.8, repeat: Infinity }}
          >
            _
          </motion.span>
        </motion.p>

        {/* Percentage */}
        <motion.p
          className="text-white/30 text-xs mt-2 font-mono"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
        >
          {progress.toString().padStart(3, '0')}%
        </motion.p>
      </div>

      {/* Corner decorations */}
      <div className="absolute top-8 left-8 w-16 h-16">
        <motion.div
          className="absolute top-0 left-0 w-4 h-4 border-l-2 border-t-2 border-jarvis-accentPink/50"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.2 }}
        />
        <motion.div
          className="absolute bottom-0 right-0 w-4 h-4 border-r-2 border-b-2 border-jarvis-accentPink/50"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.3 }}
        />
      </div>
      <div className="absolute top-8 right-8 w-16 h-16">
        <motion.div
          className="absolute top-0 right-0 w-4 h-4 border-r-2 border-t-2 border-jarvis-accentPink/50"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.4 }}
        />
        <motion.div
          className="absolute bottom-0 left-0 w-4 h-4 border-l-2 border-b-2 border-jarvis-accentPink/50"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.5 }}
        />
      </div>
      <div className="absolute bottom-8 left-8 w-16 h-16">
        <motion.div
          className="absolute bottom-0 left-0 w-4 h-4 border-l-2 border-b-2 border-jarvis-accentPink/50"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.6 }}
        />
      </div>
      <div className="absolute bottom-8 right-8 w-16 h-16">
        <motion.div
          className="absolute bottom-0 right-0 w-4 h-4 border-r-2 border-b-2 border-jarvis-accentPink/50"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.7 }}
        />
      </div>
    </motion.div>
  );
}
