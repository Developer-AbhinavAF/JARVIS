import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
  Send,
  Mic,
  Copy,
  Volume2,
  Trash2,
  AlertCircle,
  Paperclip,
  X,
  FileText,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useChat } from '@/hooks/useApi';
import type { Message, MessageAction, MessageActions } from '@/types';
import { extractResponseText } from '@/lib/jarvisProtocol';
import { JarvisMessage } from './JarvisMessage';
import { ImageResultCard, ImageGallery, type ImageResultData } from './ImageResult';
import { ImageLightbox } from './ImageLightbox';

const ACTION_LABELS: Record<string, string> = {
  open_app: '🚀 Opened App',
  close_app: '❌ Closed App',
  open_url: '🌐 Opened Link',
  search: '🔍 Search Started',
  web_search: '🔍 Web Search',
  screenshot: '📸 Screenshot',
  add_todo: '✅ Todo Added',
  add_note: '📝 Note Saved',
  clear_memory: '🧠 Memory Cleared',
  list_apps: '📋 Running Apps',
  show_todos: '🗒️ Todo List',
  show_notes: '📚 Notes',
  help: '❓ Help',
  system_status: '📊 System Status',
  daily_briefing: '📅 Briefing',
  calculator: '🧮 Calculation',
  weather: '🌤️ Weather',
  joke: '😄 Joke',
  quote: '💬 Quote',
  time: '🕒 Time',
  date: '📅 Date',
  network_status: '📶 Network Status',
  process_info: '⚙️ Process Info',
  random_fact: '🤔 Random Fact',
  read_document: '📄 Document Read',
  file_analyzed: '📄 File Analyzed',
  volume: '🔊 Volume',
  brightness: '☀️ Brightness',
  night_mode: '🌙 Night Mode',
  shutdown: '⚠️ Shutdown',
  cancel_shutdown: '✅ Shutdown Cancelled',
  restart: '🔄 Restart',
  sleep: '💤 Sleep',
  lock: '🔒 Screen Locked',
  wifi_toggle: '📶 Wi‑Fi Toggled',
  bluetooth_toggle: '🔵 Bluetooth',
  play_media: '▶️ Media Play',
  pause_media: '⏸️ Media Pause',
  next_media: '⏭️ Next Track',
  previous_media: '⏮️ Previous Track',
  stop_media: '⏹️ Media Stop',
  empty_recycle: '🗑️ Recycle Bin Emptied',
  task_manager: '📊 Task Manager',
  terminal: '💻 Terminal',
  execute: '⚡ Execute',
};

function getActionLabel(action: MessageAction): string {
  if (action.type === 'volume' && action.action) {
    return `🔊 Volume ${action.action}`;
  }
  if (action.type === 'brightness' && action.action) {
    return `☀️ Brightness ${action.action}`;
  }
  if (action.type === 'calculator' && action.result !== undefined) {
    return `🧮 Result ${action.result}`;
  }
  if (action.type === 'read_document' && action.file_name) {
    return `📄 ${action.file_name}`;
  }
  if (action.type === 'file_analyzed' && action.filename) {
    return `📄 ${action.filename}`;
  }
  if (action.type === 'media' && action.action) {
    return `🎵 Media ${action.action.replace(/_/g, ' ')}`;
  }
  return ACTION_LABELS[action.type] ?? `⚡ ${action.type.replace(/_/g, ' ')}`;
}

function executeFrontendAction(action: MessageAction) {
  switch (action.type) {
    case 'open_url':
    case 'web_search':
    case 'search':
      if (action.url) {
        window.open(action.url, '_blank', 'noopener,noreferrer');
      }
      break;
    default:
      console.log('JARVIS action:', action);
      break;
  }
}

interface ChatResponse {
  response: string;
  actions?: MessageAction[];
  suggestions?: string[];
  intent?: string;
  intent_confidence?: number;
  tool?: string;
  verified?: boolean;
  total_ms?: number;
}

export default function ChatPanel() {
  const { messages, addMessage, deleteMessage, clearMessages, isTyping, setIsTyping, mode, input, setInput, chatExpandMode, cycleExpandMode } = useStore();
  const [error, setError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<{ name: string; type: string; data: string } | null>(null);
  const [lightboxImage, setLightboxImage] = useState<{ src: string; title: string } | null>(null);
  const { loading } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingIntervalRef = useRef<number | null>(null);

  // Virtual scroll setup
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,
    overscan: 5,
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const clearTypingInterval = useCallback(() => {
    if (typingIntervalRef.current !== null) {
      window.clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }
  }, []);

  useEffect(() => clearTypingInterval, [clearTypingInterval]);

  // Listen for quick-action events from TopBar
  useEffect(() => {
    const handler = (e: CustomEvent<string>) => {
      const command = e.detail;
      if (command) {
        setInput(command);
        // Send immediately
        setTimeout(() => {
          handleSend(command);
        }, 0);
      }
    };
    window.addEventListener('quick-action', handler as EventListener);
    return () => window.removeEventListener('quick-action', handler as EventListener);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Listen for format-chat events from keyboard shortcuts
  useEffect(() => {
    const handler = (e: CustomEvent<{ format: string }>) => {
      applyFormat(e.detail.format as 'bold' | 'italic' | 'bullet' | 'numbered' | 'check' | 'quote' | 'code');
    };
    window.addEventListener('format-chat', handler as EventListener);
    return () => window.removeEventListener('format-chat', handler as EventListener);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input]);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError('File too large. Max size is 10MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      setUploadedFile({
        name: file.name,
        type: file.type,
        data: base64.split(',')[1],
      });
    };
    reader.readAsDataURL(file);
  }, []);

  const handleSend = useCallback(async (messageOverride?: string) => {
    const nextMessage = messageOverride ?? input;
    if ((!nextMessage.trim() && !uploadedFile) || loading) return;

    const userMessage = nextMessage.trim();
    setInput('');
    setError(null);
    clearTypingInterval();

    if (userMessage.toLowerCase() === '/clean' || userMessage.toLowerCase() === '/clear') {
      clearMessages();
      addMessage({ role: 'assistant', content: '**Chat cleared.**\n\nHow can I help you?' });
      return;
    }

    const messageContent = uploadedFile
      ? `${userMessage}${userMessage ? '\n\n' : ''}[Attached: ${uploadedFile.name}]`
      : userMessage;

    addMessage({ 
      role: 'user', 
      content: messageContent,
      imageAttachment: uploadedFile ? {
        data: uploadedFile.data,
        type: uploadedFile.type,
        name: uploadedFile.name,
      } : undefined,
    });
    setIsTyping(true);

    try {
      if (uploadedFile) {
        const formData = new FormData();
        formData.append('message', userMessage || `Analyze this ${uploadedFile.type.includes('image') ? 'image' : 'file'}`);
        formData.append('session_id', 'default');
        formData.append('file_name', uploadedFile.name);
        formData.append('file_type', uploadedFile.type);
        formData.append('file_data', uploadedFile.data);
        const res = await fetch('http://localhost:8001/api/chat', { method: 'POST', body: formData });
        const response: ChatResponse = await res.json();
        setUploadedFile(null);
        if (response.actions && response.actions.length > 0) response.actions.forEach(executeFrontendAction);
        addMessage({ role: 'assistant', content: '', actions: { copy: true, speak: true, delete: true } as MessageActions, actionButtons: response.actions, intent: response.intent, intent_confidence: response.intent_confidence, tool: response.tool, verified: response.verified, total_ms: response.total_ms });
        const fullResponse = response.response;
        let currentIndex = 0;
        typingIntervalRef.current = window.setInterval(() => {
          if (currentIndex <= fullResponse.length) {
            const typedContent = fullResponse.slice(0, currentIndex);
            const { messages } = useStore.getState();
            if (messages.length > 0) {
              const lastIndex = messages.length - 1;
              useStore.setState({ messages: messages.map((m, i) => i === lastIndex ? { ...m, content: typedContent } : m) });
            }
            currentIndex += 3;
            if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
          } else { clearTypingInterval(); }
        }, 15);
      } else {
        addMessage({ role: 'assistant', content: '', actions: { copy: true, speak: true, delete: true } as MessageActions });
        const res = await fetch('http://localhost:8001/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage, session_id: 'default', stream: true }),
        });
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '', fullResponse = '', actions: MessageAction[] = [], displayIndex = 0, streamDone = false;
        let metaIntent = '', metaConfidence = 0, metaTool = '', metaVerified = false, metaMs = 0;
        let imageResults: ImageResultData[] = [];
        let imageGallery: { source: string; query: string; results: ImageResultData[]; count: number } | null = null;
        clearTypingInterval();
        typingIntervalRef.current = window.setInterval(() => {
          if (displayIndex < fullResponse.length) {
            displayIndex = Math.min(displayIndex + 3, fullResponse.length);
            const { messages } = useStore.getState();
            if (messages.length > 0) {
              const lastIndex = messages.length - 1;
              useStore.setState({ messages: messages.map((m, i) => i === lastIndex ? { ...m, content: fullResponse.slice(0, displayIndex) } : m) });
            }
            if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
          } else if (streamDone) {
            clearTypingInterval();
          }
        }, 20);
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) fullResponse += data.token;
              if (data.image_result) {
                imageResults.push(data.image_result);
              }
              if (data.image_gallery) {
                imageGallery = data.image_gallery;
              }
              if (data.code_execution) {
                // Code execution result — append info to response
                const ce = data.code_execution;
                if (!ce.success) {
                  fullResponse += `\n\n[Code execution: ${ce.language}] ${ce.stderr || 'failed'}`;
                }
              }
              if (data.execute) {
                // Execute tag result — append info to response
                const ex = data.execute;
                if (ex.status === 'success') {
                  fullResponse += `\n\n[Executed: ${ex.execution_type}] ${ex.command.substring(0, 50)}${ex.command.length > 50 ? '...' : ''} ✓`;
                } else {
                  fullResponse += `\n\n[Execution failed: ${ex.execution_type}] ${ex.error || ex.stderr || 'exit code ' + ex.exit_code}`;
                }
              }
              if (data.done) {
                fullResponse = data.response || fullResponse;
                actions = data.actions || [];
                metaIntent = data.intent || '';
                metaConfidence = data.intent_confidence || 0;
                metaTool = data.tool || '';
                metaVerified = data.verified || false;
                metaMs = data.total_ms || 0;
              }
            } catch { /* skip malformed SSE */ }
          }
        }
        streamDone = true;
        const { messages } = useStore.getState();
        if (messages.length > 0) {
          const lastIndex = messages.length - 1;
          useStore.setState({ messages: messages.map((m, i) => i === lastIndex ? { ...m, content: fullResponse, actionButtons: actions, intent: metaIntent, intent_confidence: metaConfidence, tool: metaTool, verified: metaVerified, total_ms: metaMs, imageResults: imageResults.length > 0 ? imageResults : undefined, imageGallery: imageGallery || undefined } : m) });
        }
        if (actions.length > 0) actions.forEach(executeFrontendAction);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to connect to JARVIS AI';
      setError(errorMsg);
      addMessage({ role: 'assistant', content: `⚠️ **Connection Error**\n\nI couldn't process your request. Please ensure:\n1. The backend server is running (python jarvis_api.py)\n2. Check your internet connection\n3. Try again in a moment\n\nError: ${errorMsg}` });
    } finally {
      setIsTyping(false);
    }
  }, [input, uploadedFile, loading, setInput, clearTypingInterval, clearMessages, addMessage, setIsTyping]);

  const applyFormat = useCallback((format: 'bold' | 'italic' | 'bullet' | 'numbered' | 'check' | 'quote' | 'code') => {
    const textarea = inputRef.current;
    const start = textarea?.selectionStart ?? input.length;
    const end = textarea?.selectionEnd ?? input.length;
    const selected = input.slice(start, end);
    const before = input.slice(0, start);
    const after = input.slice(end);

    const linePrefix = (prefix: string, fallback: string) => {
      const source = selected || fallback;
      return source
        .split('\n')
        .map((line) => `${prefix}${line || fallback}`)
        .join('\n');
    };

    const replacements: Record<typeof format, string> = {
      bold: `**${selected || 'bold text'}**`,
      italic: `*${selected || 'italic text'}*`,
      bullet: linePrefix('- ', 'List item'),
      numbered: (selected || 'First item\nSecond item')
        .split('\n')
        .map((line, index) => `${index + 1}. ${line || `Item ${index + 1}`}`)
        .join('\n'),
      check: linePrefix('- [ ] ', 'Task item'),
      quote: linePrefix('> ', 'Quoted text'),
      code: selected.includes('\n') ? `\`\`\`\n${selected || 'code'}\n\`\`\`` : `\`${selected || 'code'}\``,
    };

    const replacement = replacements[format];
    const nextInput = `${before}${replacement}${after}`;
    setInput(nextInput);

    window.requestAnimationFrame(() => {
      textarea?.focus();
      const cursor = before.length + replacement.length;
      textarea?.setSelectionRange(cursor, cursor);
    });
  }, [input, setInput]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text);
  }, []);

  const speakText = useCallback((text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1;
      utterance.pitch = 1;
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  const onCycleExpand = useCallback(() => {
    cycleExpandMode();
  }, [cycleExpandMode]);

  // Memoize the last AI index
  const lastAIIndex = useMemo(() => {
    return [...messages].reverse().findIndex(m => m.role === 'assistant');
  }, [messages]);

  return (
    <>
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Messages Area - Virtual Scrolled */}
      <div
        ref={(node) => {
          (parentRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
          (scrollRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
        }}
        className="flex-1 overflow-y-auto px-3 py-2"
        style={{ scrollBehavior: 'smooth' }}
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const message = messages[virtualRow.index];
            const isLastAI = lastAIIndex !== -1 && virtualRow.index === messages.length - 1 - lastAIIndex;
            return (
              <div
                key={message.id}
                data-index={virtualRow.index}
                ref={virtualizer.measureElement}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                  <MessageBubble
                    message={message}
                    isFirst={virtualRow.index === 0}
                    isLastAI={isLastAI}
                    onCopy={() => copyToClipboard(message.content)}
                    onSpeak={() => speakText(extractResponseText(message.content))}
                    onDelete={() => deleteMessage(message.id)}
                    chatExpandMode={chatExpandMode}
                    onCycleExpand={onCycleExpand}
                  />
              </div>
            );
          })}
        </div>

        {/* Typing Indicator */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="flex items-center gap-2 text-jarvis-textMuted py-2"
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
            <span className="text-xs">JARVIS is thinking...</span>
          </motion.div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="mx-3 mb-2 p-2 rounded-lg bg-red-500/20 border border-red-500/30 flex items-center gap-2"
        >
          <AlertCircle size={14} className="text-red-400" />
          <span className="text-xs text-red-200">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-[10px] text-red-300 hover:text-red-100"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      {/* Input Area */}
      <div className="px-3 pb-3">
        {/* File Upload Preview */}
        <AnimatePresence>
          {uploadedFile && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-2 flex items-center gap-3 p-2 rounded-xl bg-jarvis-accentPink/10 border border-jarvis-accentPink/30"
            >
              {uploadedFile.type.startsWith('image/') ? (
                <div className="relative w-12 h-12 rounded-lg overflow-hidden bg-black/40 flex-shrink-0">
                  <img
                    src={`data:${uploadedFile.type};base64,${uploadedFile.data}`}
                    alt="Preview"
                    className="w-full h-full object-cover"
                  />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-jarvis-accentPink/30 to-jarvis-accentRed/30 flex items-center justify-center flex-shrink-0">
                  <FileText size={22} className="text-jarvis-accentPink" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-jarvis-text truncate">{uploadedFile.name}</p>
                <p className="text-[10px] text-jarvis-textMuted">
                  {(uploadedFile.data.length * 0.75 / 1024 / 1024).toFixed(2)} MB
                  {uploadedFile.type.startsWith('image/') ? ' • Image' : uploadedFile.type.startsWith('video/') ? ' • Video' : ` • ${uploadedFile.type.split('/')[1]?.toUpperCase() || 'File'}`}
                </p>
              </div>
              <motion.button
                onClick={() => setUploadedFile(null)}
                className="p-1.5 rounded-lg hover:bg-white/10 text-jarvis-textMuted hover:text-red-400 transition-colors"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <X size={16} />
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-end ml-72 bottom-4 gap-2 glass-panel rounded-2xl p-2 max-w-2xl">
          {/* Mode Indicator */}
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
              mode === 'text' ? 'bg-jarvis-accentRed/20' : 'bg-jarvis-accentPink/20'
            }`}
          >
            {mode === 'text' ? (
              <span className="text-jarvis-accentRed text-sm font-medium">T</span>
            ) : (
              <Mic size={16} className="text-jarvis-accentPink" />
            )}
          </div>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*,.pdf,.txt,.doc,.docx"
            onChange={handleFileUpload}
            className="hidden"
          />

          {/* File Upload Button */}
          <motion.button
            onClick={() => fileInputRef.current?.click()}
            disabled={loading || !!uploadedFile}
            className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all shrink-0 ${
              uploadedFile
                ? 'bg-jarvis-accentPink/30 text-jarvis-accentPink'
                : 'bg-white/5 text-jarvis-textMuted hover:text-jarvis-text hover:bg-white/10'
            }`}
            whileHover={!uploadedFile ? { scale: 1.05 } : {}}
            whileTap={!uploadedFile ? { scale: 0.95 } : {}}
            title="Upload file, image, or video (max 10MB)"
          >
            <Paperclip size={16} />
          </motion.button>

          {/* Text Input */}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={uploadedFile ? "Ask about the file... (or just send)" : "Message JARVIS..."}
            className="max-h-28 min-h-9 flex-1 resize-none bg-transparent py-2 text-sm leading-5 text-jarvis-text placeholder-jarvis-textMuted outline-none scrollbar-visible"
            disabled={loading}
            rows={1}
          />

          {/* Send Button */}
          <motion.button
            onClick={() => {
              void handleSend();
            }}
            disabled={(!input.trim() && !uploadedFile) || loading}
            className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all shrink-0 ${
              (input.trim() || uploadedFile) && !loading
                ? 'bg-gradient-to-r from-jarvis-accentPink to-jarvis-accentRed text-white'
                : 'bg-white/5 text-jarvis-textMuted'
            }`}
            whileHover={(input.trim() || uploadedFile) && !loading ? { scale: 1.05 } : {}}
            whileTap={(input.trim() || uploadedFile) && !loading ? { scale: 0.95 } : {}}
          >
            {mode === 'speech' && !input.trim() && !uploadedFile ? (
              <Mic size={16} />
            ) : (
              <Send size={16} />
            )}
          </motion.button>
        </div>
      </div>
    </div>

    {/* Image Lightbox */}
    <AnimatePresence>
      {lightboxImage && (
        <ImageLightbox
          src={lightboxImage.src}
          title={lightboxImage.title}
          onClose={() => setLightboxImage(null)}
        />
      )}
    </AnimatePresence>
  </>
  );
}

interface MessageBubbleProps {
  message: Message;
  isFirst: boolean;
  isLastAI: boolean;
  onCopy: () => void;
  onSpeak: () => void;
  onDelete: () => void;
  chatExpandMode: 'normal' | 'half' | 'full';
  onCycleExpand: () => void;
}

const MessageBubble = React.memo(function MessageBubble({
  message,
  isFirst,
  isLastAI,
  onCopy,
  onSpeak,
  onDelete,
  chatExpandMode,
  onCycleExpand,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [showActions, setShowActions] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12, scale: 0.97 }}
      transition={{
        duration: 0.25,
        layout: { duration: 0.15 }
      }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      onMouseEnter={() => { setShowActions(true); setIsHovered(true); }}
      onMouseLeave={() => { setShowActions(false); setIsHovered(false); }}
    >
      <motion.div
        animate={{
          boxShadow: isHovered
            ? isUser
              ? '0 6px 24px rgba(239, 68, 68, 0.25)'
              : '0 6px 24px rgba(255, 255, 255, 0.08)'
            : '0 0px 0px rgba(0, 0, 0, 0)'
        }}
        transition={{ duration: 0.15 }}
        className={`max-w-[85%] rounded-2xl px-3 py-2.5 relative ${
          isUser
            ? 'bg-gradient-to-r from-jarvis-accentRed to-red-600 text-white rounded-br-md'
            : 'glass-panel rounded-bl-md'
        }`}
      >
        {/* Message Content */}
        {isFirst && !isUser ? (
          <div className="space-y-1">
            <h2 className="text-base font-semibold">Hello, I'm JARVIS.</h2>
            <p className="text-jarvis-textMuted text-xs">I'm your fully functional AI assistant. I can control your system, search the web, manage your tasks, and more. What can I do for you?</p>
          </div>
        ) : (
          <div className="space-y-1">
            {/* Image Attachment */}
            {message.imageAttachment && (
              <div 
                className="relative w-32 h-32 rounded-lg overflow-hidden bg-black/20 cursor-pointer hover:opacity-90 transition-opacity"
                onClick={() => setLightboxImage({
                  src: `data:${message.imageAttachment.type};base64,${message.imageAttachment.data}`,
                  title: message.imageAttachment.name,
                })}
              >
                <img
                  src={`data:${message.imageAttachment.type};base64,${message.imageAttachment.data}`}
                  alt={message.imageAttachment.name}
                  className="w-full h-full object-cover"
                />
              </div>
            )}
            {!isUser ? (
              <JarvisMessage content={message.content} />
            ) : (
              <p className="text-[13px] leading-relaxed whitespace-pre-wrap">
                {message.content}
              </p>
            )}
            {/* Image Gallery */}
            {message.imageGallery && message.imageGallery.results.length > 0 && (
              <div className="mt-2">
                <ImageGallery
                  source={message.imageGallery.source}
                  query={message.imageGallery.query}
                  results={message.imageGallery.results}
                  count={message.imageGallery.count}
                />
              </div>
            )}
            {/* Single/Multiple Image Results */}
            {message.imageResults && message.imageResults.length > 0 && !message.imageGallery && (
              <div className="mt-2 flex flex-wrap gap-2">
                {message.imageResults.map((img, idx) => (
                  <ImageResultCard key={idx} result={img} compact={message.imageResults!.length > 1} />
                ))}
              </div>
            )}
            {message.actionButtons && message.actionButtons.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5 pt-1.5 border-t border-white/10">
                {message.actionButtons.map((action: MessageAction, idx: number) => (
                  <span
                    key={idx}
                    className="px-1.5 py-0.5 rounded text-[9px] bg-jarvis-accentPink/20 text-jarvis-accentPink"
                  >
                    {getActionLabel(action)}
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
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              className={`absolute ${
                isUser ? 'left-0 -translate-x-full' : 'right-0 translate-x-full'
              } top-1.5 flex flex-col gap-0.5`}
            >
              <button
                onClick={onCopy}
                className="p-1 rounded-lg bg-black/50 text-jarvis-textMuted hover:text-jarvis-text transition-colors"
                title="Copy"
              >
                <Copy size={12} />
              </button>
              {!isUser && (
                <button
                  onClick={onSpeak}
                  className="p-1 rounded-lg bg-black/50 text-jarvis-textMuted hover:text-jarvis-text transition-colors"
                  title="Speak"
                >
                  <Volume2 size={12} />
                </button>
              )}
              <button
                onClick={onDelete}
                className="p-1 rounded-lg bg-black/50 text-jarvis-textMuted hover:text-red-400 transition-colors"
                title="Delete"
              >
                <Trash2 size={12} />
              </button>
              {!isUser && isLastAI && (
                <button
                  onClick={onCycleExpand}
                  className="p-1 rounded-lg bg-black/50 text-jarvis-textMuted hover:text-jarvis-accentPink transition-colors"
                  title={chatExpandMode === 'normal' ? 'Expand canvas' : chatExpandMode === 'half' ? 'Full screen' : 'Reset canvas'}
                >
                  {chatExpandMode === 'normal' || chatExpandMode === 'half' ? <Maximize2 size={12} /> : <Minimize2 size={12} />}
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Timestamp */}
        <span
          className={`text-[9px] mt-1 block ${
            isUser ? 'text-white/60' : 'text-jarvis-textMuted'
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </motion.div>
    </motion.div>
  );
}, (prev, next) => {
  return prev.message.id === next.message.id
    && prev.message.content === next.message.content
    && prev.isLastAI === next.isLastAI
    && prev.chatExpandMode === next.chatExpandMode
    && prev.isFirst === next.isFirst;
});
