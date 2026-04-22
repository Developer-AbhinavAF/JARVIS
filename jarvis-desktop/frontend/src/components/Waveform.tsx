import { motion } from 'framer-motion';

interface WaveformProps {
  isActive: boolean;
  barCount?: number;
}

export default function Waveform({ isActive, barCount = 16 }: WaveformProps) {
  return (
    <div className="flex items-center gap-0.5 h-8">
      {/* Center Icon */}
      <motion.div
        className="w-8 h-8 rounded-full flex items-center justify-center"
        animate={
          isActive
            ? {
                boxShadow: [
                  '0 0 10px rgba(255, 110, 199, 0.3)',
                  '0 0 30px rgba(255, 110, 199, 0.6)',
                  '0 0 10px rgba(255, 110, 199, 0.3)',
                ],
              }
            : {}
        }
        transition={{ duration: 1.5, repeat: Infinity }}
        style={{
          background: isActive
            ? 'linear-gradient(135deg, #ff6ec7 0%, #cc58a0 100%)'
            : 'rgba(255, 110, 199, 0.2)',
        }}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="22" />
        </svg>
      </motion.div>

      {/* Left Bars */}
      <div className="flex items-center gap-[2px] ml-2">
        {Array.from({ length: barCount / 2 }).map((_, i) => (
          <motion.div
            key={`left-${i}`}
            className="w-1 bg-jarvis-accentPink rounded-full"
            animate={
              isActive
                ? {
                    height: [4, 16 + Math.random() * 16, 4],
                    opacity: [0.5, 1, 0.5],
                  }
                : { height: 4, opacity: 0.3 }
            }
            transition={{
              duration: 0.5 + Math.random() * 0.3,
              repeat: Infinity,
              delay: i * 0.05,
              ease: 'easeInOut',
            }}
            style={{
              background: isActive
                ? 'linear-gradient(to top, #ff6ec7, #ff3b3b)'
                : 'rgba(255, 110, 199, 0.3)',
            }}
          />
        ))}
      </div>

      {/* Right Bars */}
      <div className="flex items-center gap-[2px]">
        {Array.from({ length: barCount / 2 }).map((_, i) => (
          <motion.div
            key={`right-${i}`}
            className="w-1 bg-jarvis-accentPink rounded-full"
            animate={
              isActive
                ? {
                    height: [4, 16 + Math.random() * 16, 4],
                    opacity: [0.5, 1, 0.5],
                  }
                : { height: 4, opacity: 0.3 }
            }
            transition={{
              duration: 0.5 + Math.random() * 0.3,
              repeat: Infinity,
              delay: (barCount / 2 - i) * 0.05,
              ease: 'easeInOut',
            }}
            style={{
              background: isActive
                ? 'linear-gradient(to top, #ff6ec7, #ff3b3b)'
                : 'rgba(255, 110, 199, 0.3)',
            }}
          />
        ))}
      </div>
    </div>
  );
}
