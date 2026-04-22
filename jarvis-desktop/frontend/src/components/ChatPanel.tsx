import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Mic, Copy, Volume2, Trash2, CheckSquare, StickyNote, Search, ExternalLink, Terminal, AlertCircle } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useChat } from '@/hooks/useApi';
import type { Message } from '@/types';

interface ChatResponse {
  response: string;
  actions?: Array<{
    type: string;
    app?: string;
    path?: string;
    url?: string;
    query?: string;
    data?: any;
  }>;
  suggestions?: string[];
}

export default function ChatPanel() {
  const { messages, addMessage, deleteMessage, isTyping, setIsTyping, mode } = useStore();
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
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

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setError(null);
    setSuggestions([]);

    // Add user message
    addMessage({ role: 'user', content: userMessage });
    setIsTyping(true);

    try {
      // Send to API - use real JARVIS AI
      const response: ChatResponse = await sendMessage(userMessage);
      
      // Execute any actions returned by JARVIS
      if (response.actions && response.actions.length > 0) {
        executeActions(response.actions);
      }
      
      // Update suggestions
      if (response.suggestions) {
        setSuggestions(response.suggestions);
      }
      
      // Add AI response
      addMessage({ 
        role: 'assistant', 
        content: response.response,
        actions: response.actions 
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to connect to JARVIS AI';
      setError(errorMsg);
      addMessage({
        role: 'assistant',
        content: `⚠️ **Connection Error**\n\nI couldn't process your request. Please ensure:\n1. The backend server is running (python jarvis_api.py)\n2. Check your internet connection\n3. Try again in a moment\n\nError: ${errorMsg}`,
      });
    } finally {
      setIsTyping(false);
    }
  }, [input, loading, addMessage, setIsTyping, sendMessage]);

  // Execute actions returned by JARVIS
  const executeActions = useCallback((actions: ChatResponse['actions']) => {
    if (!actions) return;
    
    actions.forEach(action => {
      switch (action.type) {
        case 'open_url':
          if (action.url) {
            window.open(action.url, '_blank');
          }
          break;
        case 'screenshot':
          // Screenshot was already taken on backend
          console.log('Screenshot saved:', action.path);
          break;
        case 'add_todo':
        case 'add_note':
          // Memory items were already saved on backend
          console.log('Memory saved:', action);
          break;
      }
    });
  }, []);

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

      {/* AI Suggestions */}
      {suggestions.length > 0 && (
        <div className="px-6 py-2">
          <p className="text-xs text-jarvis-textMuted mb-2">Suggested:</p>
          <div className="flex gap-2 overflow-x-auto">
            {suggestions.map((suggestion, index) => (
              <motion.button
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
                className="px-3 py-1.5 rounded-lg bg-jarvis-accentPink/10 text-sm text-jarvis-accentPink hover:bg-jarvis-accentPink/20 transition-all"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  setInput(suggestion);
                  inputRef.current?.focus();
                }}
              >
                {suggestion}
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="px-6 py-3 flex gap-2 overflow-x-auto">
        {[
          { label: 'Take Screenshot', icon: Terminal, command: 'take screenshot' },
          { label: 'Open YouTube', icon: ExternalLink, command: 'open youtube' },
          { label: 'System Status', icon: Terminal, command: 'system status' },
          { label: 'Daily Briefing', icon: CheckSquare, command: 'daily briefing' },
        ].map((action) => {
          const Icon = action.icon;
          return (
            <motion.button
              key={action.label}
              className="px-4 py-2 rounded-lg glass-panel text-sm text-jarvis-textMuted hover:text-jarvis-text whitespace-nowrap transition-all flex items-center gap-2"
              whileHover={{ scale: 1.02, backgroundColor: 'rgba(255,255,255,0.08)' }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                setInput(action.command);
                handleSend();
              }}
            >
              <Icon size={14} />
              {action.label}
            </motion.button>
          );
        })}
      </div>

      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="mx-6 mb-3 p-3 rounded-lg bg-red-500/20 border border-red-500/30 flex items-center gap-2"
        >
          <AlertCircle size={16} className="text-red-400" />
          <span className="text-sm text-red-200">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-xs text-red-300 hover:text-red-100"
          >
            Dismiss
          </button>
        </motion.div>
      )}

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
          JARVIS is fully functional • Try: "open chrome", "system status", "add todo buy milk"
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
            <p className="text-jarvis-textMuted">I'm your fully functional AI assistant. I can control your system, search the web, manage your tasks, and more. What can I do for you?</p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
            {/* Show action badges */}
            {message.actions && message.actions.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-white/10">
                {message.actions.map((action, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded text-[10px] bg-jarvis-accentPink/20 text-jarvis-accentPink"
                  >
                    {action.type === 'open_app' && '🚀 Opened'}
                    {action.type === 'close_app' && '❌ Closed'}
                    {action.type === 'screenshot' && '📸 Screenshot'}
                    {action.type === 'web_search' && '🔍 Search'}
                    {action.type === 'add_todo' && '✅ Todo Added'}
                    {action.type === 'add_note' && '📝 Note Saved'}
                    {action.type === 'volume' && `🔊 ${action.action}`}
                    {action.type === 'system_status' && '📊 System Status'}
                    {action.type === 'daily_briefing' && '📅 Briefing'}
                  </span>
                ))}
              </div>
            )}
          </div>
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
