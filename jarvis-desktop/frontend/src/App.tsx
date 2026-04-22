import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import ChatPanel from '@/components/ChatPanel';
import RightPanel from '@/components/RightPanel';
import BottomBar from '@/components/BottomBar';
import { useStore } from '@/store/useStore';
import { useWebSocket } from '@/hooks/useWebSocket';

function App() {
  const { mode, isListening, setIsListening, setSystemStats, setIsConnected } = useStore();
  const { lastMessage, isConnected } = useWebSocket('ws://localhost:8000/ws');

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data);
        if (data.type === 'system_stats') {
          setSystemStats(data.payload);
        } else if (data.type === 'listening_state') {
          setIsListening(data.payload.isListening);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    }
  }, [lastMessage, setSystemStats, setIsListening]);

  useEffect(() => {
    setIsConnected(isConnected);
  }, [isConnected, setIsConnected]);

  return (
    <div className="h-screen w-screen bg-jarvis-bg flex overflow-hidden font-sans text-jarvis-text">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar with Mode Toggle */}
        <TopBar />

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Panel */}
          <motion.div
            className="flex-1 flex flex-col min-w-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {/* Listening Indicator */}
            <AnimatePresence>
              {isListening && mode === 'speech' && (
                <motion.div
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="flex items-center justify-center py-2 text-jarvis-accentPink text-sm font-medium"
                >
                  <span className="animate-pulse mr-2">●</span>
                  Listening...
                </motion.div>
              )}
            </AnimatePresence>

            {/* Chat Area */}
            <ChatPanel />
          </motion.div>

          {/* Right Panel - System Dashboard & Plugins */}
          <RightPanel />
        </div>

        {/* Bottom Quick Actions Bar */}
        <BottomBar />
      </div>
    </div>
  );
}

export default App;
