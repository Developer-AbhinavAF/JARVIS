import { useEffect, useCallback, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import ChatPanel from '@/components/ChatPanel';
import RightPanel from '@/components/RightPanel';
import BottomBar from '@/components/BottomBar';
import DashboardSection from '@/components/DashboardSection';
import PCControlSection from '@/components/PCControlSection';
import MemorySection from '@/components/MemorySection';
import LogsSection from '@/components/LogsSection';
import HomeSection from '@/components/HomeSection';
import SettingsSection from '@/components/SettingsSection';
import DocsSection from '@/components/DocsSection';
import { useStore } from '@/store/useStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';
import { Mic, MicOff, Send } from 'lucide-react';

function App() {
  const { setIsListening, setSystemStats, setIsConnected, activeTab, addMessage, setIsTyping, mode: currentMode, toggleMode } = useStore();
  const { lastMessage, isConnected } = useWebSocket('ws://localhost:8001/ws');
  const { isListening: speechListening, transcript, interimTranscript, startListening, stopListening, resetTranscript, isSupported, error: speechError } = useSpeechRecognition();
  const [isSpeaking, setIsSpeaking] = useState(false);
  const lastProcessedTranscript = useRef('');

  // Text-to-speech function
  const speakText = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) return;
    
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;
    
    // Try to find a good English voice
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.name.includes('Google US English')) 
      || voices.find(v => v.name.includes('Microsoft David'))
      || voices.find(v => v.lang === 'en-US' && v.name.includes('Male'))
      || voices.find(v => v.lang === 'en-US')
      || voices[0];
    
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }
    
    utterance.onstart = () => {
      setIsSpeaking(true);
    };
    
    utterance.onend = () => {
      setIsSpeaking(false);
      // In speech mode, restart listening after AI finishes speaking
      if (currentMode === 'speech') {
        setTimeout(() => {
          startListening();
        }, 500); // Small delay for natural conversation flow
      }
    };
    
    utterance.onerror = () => {
      setIsSpeaking(false);
    };
    
    window.speechSynthesis.speak(utterance);
  }, [currentMode, startListening]);

  // Send voice message when transcript is ready
  const sendVoiceMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;
    
    // Prevent processing the same transcript twice
    if (text.trim() === lastProcessedTranscript.current) return;
    lastProcessedTranscript.current = text.trim();
    
    // Add user message
    addMessage({ role: 'user', content: text.trim() });
    setIsTyping(true);
    
    try {
      const response = await fetch('http://localhost:8001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text.trim(), session_id: 'default' }),
      });
      
      const data = await response.json();
      
      // Add AI response
      addMessage({
        role: 'assistant',
        content: data.response,
        actions: data.actions,
      });
      
      // Execute any actions
      if (data.actions) {
        data.actions.forEach((action: any) => {
          if (action.type === 'open_url' && action.url) {
            window.open(action.url, '_blank');
          }
        });
      }
      
      // In speech mode, speak the response
      if (currentMode === 'speech') {
        // Clean up the response text for better speech (remove markdown, emojis, system stats)
        let cleanText = data.response
          .replace(/\*\*/g, '')  // Remove bold
          .replace(/\*/g, '')   // Remove italic
          .replace(/🚀|📊|🔍|💡|⚠️|✅|❌|🎤|🤖|🧮|🌤️|😄|💫|📡|⚙️|🤔|⬜|✅|🖥️|⚡|🔍|🧰|📝|ℹ️|🎮|🔇|🔊|🔉|▶️|⏭️|⏮️|🔄|💤|🔒|📶|🔵|🗑️|💻/g, '') // Remove all emojis
          .replace(/\n/g, ' ')  // Replace newlines with spaces
          .trim();
        
        // Remove system stats / CPU / Memory warnings from speech
        const lines = cleanText.split('. ');
        const filteredLines = lines.filter((line: string) => {
          const lower = line.toLowerCase();
          return !lower.includes('cpu usage') && 
                 !lower.includes('memory usage') && 
                 !lower.includes('ram usage') &&
                 !lower.includes('battery at') &&
                 !lower.includes('system status') &&
                 !lower.includes('disk usage') &&
                 !lower.includes('network speed') &&
                 !lower.includes('processes running');
        });
        cleanText = filteredLines.join('. ');
        
        // Limit speech length for faster response
        if (cleanText.length > 200) {
          cleanText = cleanText.substring(0, 200) + '. I\'ve shown more details in the chat.';
        }
        
        speakText(cleanText);
      }
    } catch (err) {
      const errorMsg = 'Sorry, I couldn\'t process your request. Please try again.';
      addMessage({
        role: 'assistant',
        content: errorMsg,
      });
      if (currentMode === 'speech') {
        speakText(errorMsg);
      }
    } finally {
      setIsTyping(false);
    }
  }, [addMessage, setIsTyping, currentMode, speakText]);

  // Handle speech mode toggle
  useEffect(() => {
    if (currentMode === 'speech') {
      if (!isSupported) {
        toggleMode(); // Switch back to text if not supported
        return;
      }
      startListening();
    } else {
      stopListening();
    }
  }, [currentMode, isSupported, startListening, stopListening, toggleMode]);

  // Handle speech transcript completion - ONLY in speech mode
  useEffect(() => {
    if (currentMode === 'speech' && transcript && !speechListening && !isSpeaking) {
      // Speech has ended and AI is not speaking, send the message
      sendVoiceMessage(transcript);
      resetTranscript();
    }
  }, [currentMode, transcript, speechListening, isSpeaking, sendVoiceMessage, resetTranscript]);

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

  // Render the active section
  const renderSection = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardSection />;
      case 'pc-control':
        return <PCControlSection />;
      case 'memory':
        return <MemorySection />;
      case 'logs':
        return <LogsSection />;
      case 'home':
        return <HomeSection />;
      case 'assistant':
        return <ChatPanel />;
      case 'settings':
        return <SettingsSection />;
      case 'help':
        return <DocsSection />;
      default:
        return <HomeSection />;
    }
  };

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
          {/* Main Panel */}
          <motion.div
            className="flex-1 flex flex-col min-w-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {/* Listening / Speaking Indicator */}
            <AnimatePresence>
              {currentMode === 'speech' && (
                <motion.div
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className={`flex items-center justify-center py-3 px-4 border-b ${isSpeaking ? 'bg-jarvis-accentRed/10 border-jarvis-accentRed/20' : 'bg-jarvis-accentPink/10 border-jarvis-accentPink/20'}`}
                >
                  <div className="flex items-center gap-3">
                    {/* Status Icon */}
                    {isSpeaking ? (
                      <div className="p-2 rounded-full bg-jarvis-accentRed animate-pulse">
                        <div className="flex gap-0.5 items-end h-5">
                          <div className="w-1 bg-white animate-[wave_1s_ease-in-out_infinite]" style={{ height: '60%' }} />
                          <div className="w-1 bg-white animate-[wave_1s_ease-in-out_infinite_0.1s]" style={{ height: '100%' }} />
                          <div className="w-1 bg-white animate-[wave_1s_ease-in-out_infinite_0.2s]" style={{ height: '40%' }} />
                          <div className="w-1 bg-white animate-[wave_1s_ease-in-out_infinite_0.3s]" style={{ height: '80%' }} />
                        </div>
                      </div>
                    ) : (
                      <div className={`p-2 rounded-full ${speechListening ? 'bg-jarvis-accentPink animate-pulse' : 'bg-jarvis-accentPink/50'}`}>
                        {speechListening ? <Mic size={18} className="text-white" /> : <MicOff size={18} className="text-white" />}
                      </div>
                    )}
                    
                    <div>
                      <div className={`text-sm font-medium ${isSpeaking ? 'text-jarvis-accentRed' : 'text-jarvis-accentPink'}`}>
                        {isSpeaking ? 'JARVIS is speaking...' : speechListening ? 'Listening...' : 'Click to speak'}
                      </div>
                      {!isSpeaking && (interimTranscript || transcript) && (
                        <div className="text-jarvis-text text-xs max-w-[300px] truncate">
                          {interimTranscript || transcript}
                        </div>
                      )}
                      {speechError && (
                        <div className="text-red-400 text-xs">{speechError}</div>
                      )}
                    </div>
                    
                    {transcript && !isSpeaking && (
                      <div className="ml-4 px-3 py-1 rounded-full bg-white/10 text-xs text-jarvis-text max-w-[200px] truncate">
                        {transcript}
                      </div>
                    )}
                    
                    {/* Send Now Button - for immediate sending */}
                    {!isSpeaking && speechListening && (transcript || interimTranscript) && (
                      <button
                        onClick={() => {
                          stopListening();
                          const textToSend = transcript || interimTranscript;
                          if (textToSend?.trim()) {
                            sendVoiceMessage(textToSend.trim());
                            resetTranscript();
                          }
                        }}
                        className="ml-3 flex items-center gap-1.5 px-3 py-1.5 bg-jarvis-accentPink hover:bg-jarvis-accentPink/80 text-white text-xs font-medium rounded-full transition-colors"
                      >
                        <Send size={12} />
                        Send
                      </button>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Section Content */}
            <div className="flex-1 overflow-hidden">
              {renderSection()}
            </div>
          </motion.div>

          {/* Right Panel - System Dashboard & Plugins - only show on assistant */}
          {activeTab === 'assistant' && <RightPanel />}
        </div>

        {/* Bottom Quick Actions Bar */}
        <BottomBar />
      </div>
    </div>
  );
}

export default App;
