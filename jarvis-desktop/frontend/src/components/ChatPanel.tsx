import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Mic, Copy, Volume2, Trash2, MoreHorizontal } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useChat } from '@/hooks/useApi';
import type { Message } from '@/types';

export default function ChatPanel() {
  const { messages, addMessage, deleteMessage, isTyping, setIsTyping, mode } = useStore();
  const [input, setInput] = useState('');
  const { sendMessage, loading } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
    addMessage({ role: 'user', content: userMessage });
    setIsTyping(true);

    try {
      // Send to API
      const response = await sendMessage(userMessage);
      
      // Add AI response
      addMessage({ role: 'assistant', content: response.response });
    } catch (error) {
      addMessage({
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again.',
      });
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1;
      utterance.pitch = 1;
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Messages Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-4"
      >
        <AnimatePresence initial={false}>
          {messages.map((message, index) => (
            <MessageBubble
              key={message.id}
              message={message}
              isFirst={index === 0}
              onCopy={() => copyToClipboard(message.content)}
              onSpeak={() => speakText(message.content)}
              onDelete={() => deleteMessage(message.id)}
            />
          ))}
        </AnimatePresence>

        {/* Typing Indicator */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="flex items-center gap-2 text-jarvis-textMuted"
          >
            <div className="flex gap-1">
              <motion.div
                className="w-2 h-2 rounded-full bg-jarvis-accentPink"
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 0.5, repeat: Infinity, delay: 0 }}
              />
              <motion.div
                className="w-2 h-2 rounded-full bg-jarvis-accentPink"
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 0.5, repeat: Infinity, delay: 0.1 }}
              />
              <motion.div
                className="w-2 h-2 rounded-full bg-jarvis-accentPink"
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 0.5, repeat: Infinity, delay: 0.2 }}
              />
            </div>
            <span className="text-sm">JARVIS is thinking...</span>
          </motion.div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="px-6 py-3 flex gap-2 overflow-x-auto">
        {['Take Screenshot', 'Open YouTube', 'Set Reminder', 'Daily Briefing'].map(
          (action) => (
            <motion.button
              key={action}
              className="px-4 py-2 rounded-lg glass-panel text-sm text-jarvis-textMuted hover:text-jarvis-text whitespace-nowrap transition-all"
              whileHover={{ scale: 1.02, backgroundColor: 'rgba(255,255,255,0.08)' }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                addMessage({ role: 'user', content: action.toLowerCase() });
                setIsTyping(true);
                setTimeout(() => {
                  addMessage({
                    role: 'assistant',
                    content: `I'll help you ${action.toLowerCase()}. Let me process that for you.`,
                  });
                  setIsTyping(false);
                }, 1000);
              }}
            >
              {action}
            </motion.button>
          )
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 glass-panel rounded-2xl p-2">
          {/* Mode Indicator */}
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              mode === 'text' ? 'bg-jarvis-accentRed/20' : 'bg-jarvis-accentPink/20'
            }`}
          >
            {mode === 'text' ? (
              <span className="text-jarvis-accentRed text-lg">T</span>
            ) : (
              <Mic size={20} className="text-jarvis-accentPink" />
            )}
          </div>

          {/* Text Input */}
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your command..."
            className="flex-1 bg-transparent text-jarvis-text placeholder-jarvis-textMuted outline-none text-sm"
            disabled={loading}
          />

          {/* Send Button */}
          <motion.button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              input.trim() && !loading
                ? 'bg-gradient-to-r from-jarvis-accentPink to-jarvis-accentRed text-white'
                : 'bg-white/5 text-jarvis-textMuted'
            }`}
            whileHover={input.trim() && !loading ? { scale: 1.05 } : {}}
            whileTap={input.trim() && !loading ? { scale: 0.95 } : {}}
          >
            {mode === 'speech' && !input.trim() ? (
              <Mic size={18} />
            ) : (
              <Send size={18} />
            )}
          </motion.button>
        </div>

        <p className="text-xs text-jarvis-textMuted mt-2 text-center">
          Tip: You can say "hello" to wake me up
        </p>
      </div>
    </div>
  );
}

interface MessageBubbleProps {
  message: Message;
  isFirst: boolean;
  onCopy: () => void;
  onSpeak: () => void;
  onDelete: () => void;
}

function MessageBubble({
  message,
  isFirst,
  onCopy,
  onSpeak,
  onDelete,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [showActions, setShowActions] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div
        className={`max-w-[80%] rounded-2xl p-4 relative ${
          isUser
            ? 'bg-gradient-to-r from-jarvis-accentRed to-red-600 text-white rounded-br-md'
            : 'glass-panel rounded-bl-md'
        }`}
      >
        {/* Message Content */}
        {isFirst && !isUser ? (
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Hello, I'm JARVIS.</h2>
            <p className="text-jarvis-textMuted">How can I assist you today?</p>
          </div>
        ) : (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        )}

        {/* Actions */}
        <AnimatePresence>
          {showActions && !isFirst && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className={`absolute ${
                isUser ? 'left-0 -translate-x-full' : 'right-0 translate-x-full'
              } top-2 flex flex-col gap-1`}
            >
              <button
                onClick={onCopy}
                className="p-1.5 rounded-lg bg-black/50 text-jarvis-textMuted hover:text-jarvis-text transition-colors"
                title="Copy"
              >
                <Copy size={14} />
              </button>
              {!isUser && (
                <button
                  onClick={onSpeak}
                  className="p-1.5 rounded-lg bg-black/50 text-jarvis-textMuted hover:text-jarvis-text transition-colors"
                  title="Speak"
                >
                  <Volume2 size={14} />
                </button>
              )}
              <button
                onClick={onDelete}
                className="p-1.5 rounded-lg bg-black/50 text-jarvis-textMuted hover:text-red-400 transition-colors"
                title="Delete"
              >
                <Trash2 size={14} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Timestamp */}
        <span
          className={`text-[10px] mt-2 block ${
            isUser ? 'text-white/70' : 'text-jarvis-textMuted'
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </motion.div>
  );
}
