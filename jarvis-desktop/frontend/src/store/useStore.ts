import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Mode, Message, SystemStats, Plugin, Todo, Note, Reminder, ChatSession } from '@/types';

interface StoreState {
  // Mode
  mode: Mode;
  isListening: boolean;
  setMode: (mode: Mode) => void;
  setIsListening: (listening: boolean) => void;
  toggleMode: () => void;

  // Chat
  messages: Message[];
  currentSession: string | null;
  isTyping: boolean;
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  deleteMessage: (id: string) => void;
  clearMessages: () => void;
  setIsTyping: (typing: boolean) => void;

  // System
  systemStats: SystemStats | null;
  isConnected: boolean;
  setSystemStats: (stats: SystemStats) => void;
  setIsConnected: (connected: boolean) => void;

  // Plugins
  plugins: Plugin[];
  setPlugins: (plugins: Plugin[]) => void;
  togglePlugin: (id: string) => void;

  // Navigation
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // Expand Modes: 'normal' | 'half' | 'full'
  chatExpandMode: 'normal' | 'half' | 'full';
  setChatExpandMode: (mode: 'normal' | 'half' | 'full') => void;
  cycleExpandMode: () => void;

  // Input for chat
  input: string;
  setInput: (text: string) => void;

  // File Previews
  filePreviews: Record<string, { url: string; type: string; size: number }>;
  addFilePreview: (id: string, preview: { url: string; type: string; size: number }) => void;
  removeFilePreview: (id: string) => void;

  // Memory
  todos: Todo[];
  notes: Note[];
  reminders: Reminder[];
  sessions: ChatSession[];
  addTodo: (todo: Omit<Todo, 'id' | 'createdAt'>) => void;
  toggleTodo: (id: string) => void;
  deleteTodo: (id: string) => void;
  addNote: (note: Omit<Note, 'id' | 'createdAt' | 'updatedAt'>) => void;
  updateNote: (id: string, updates: Partial<Note>) => void;
  deleteNote: (id: string) => void;
  addReminder: (reminder: Omit<Reminder, 'id'>) => void;
  deleteReminder: (id: string) => void;

  // Learning Progress
  learningProgress: {
    active: boolean;
    taskId: string | null;
    title: string;
    percent: number;
    status: string;
    logs: string[];
  };
  setLearningProgress: (progress: Partial<StoreState['learningProgress']>) => void;
  clearLearningProgress: () => void;

  // Shopping Progress
  shoppingProgress: {
    active: boolean;
    query: string;
    status: string; // "searching", "found", "completed", "error"
    platform: string;
    resultsCount: number;
    lastUpdate: string;
  };
  setShoppingProgress: (progress: Partial<StoreState['shoppingProgress']>) => void;
  clearShoppingProgress: () => void;
}

export const useStore = create<StoreState>()(
  persist(
    (set, get) => ({
      // Mode
      mode: 'text',
      isListening: false,
      setMode: (mode) => set({ mode, isListening: mode === 'speech' }),
      setIsListening: (listening) => set({ isListening: listening }),
      toggleMode: () => {
        const newMode = get().mode === 'text' ? 'speech' : 'text';
        set({ mode: newMode, isListening: newMode === 'speech' });
      },

      // Chat
      messages: [
        {
          id: 'welcome',
          role: 'assistant',
          content: "Hello, I'm JARVIS.\nHow can I assist you today?",
          timestamp: Date.now(),
          actions: { copy: true, speak: true, delete: false },
        },
      ],
      currentSession: null,
      isTyping: false,
      addMessage: (message) => {
        const newMessage: Message = {
          ...message,
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          actions: { copy: true, speak: true, delete: true },
        };
        set((state) => ({ messages: [...state.messages, newMessage] }));
      },
      deleteMessage: (id) => {
        set((state) => ({
          messages: state.messages.filter((m) => m.id !== id),
        }));
      },
      clearMessages: () => {
        set({
          messages: [
            {
              id: 'welcome',
              role: 'assistant',
              content: "Hello, I'm JARVIS.\nHow can I assist you today?",
              timestamp: Date.now(),
              actions: { copy: true, speak: true, delete: false },
            },
          ],
        });
      },
      setIsTyping: (typing) => set({ isTyping: typing }),

      // System
      systemStats: null,
      isConnected: false,
      setSystemStats: (stats) => set({ systemStats: stats }),
      setIsConnected: (connected) => set({ isConnected: connected }),

      // Plugins
      plugins: [
        {
          id: 'vision',
          name: 'Vision',
          description: 'Webcam, QR, Motion Detection',
          icon: 'Camera',
          status: 'ready',
          version: '1.0.0',
        },
        {
          id: 'ocr',
          name: 'OCR',
          description: 'Image & Screen Text Recognition',
          icon: 'Scan',
          status: 'ready',
          version: '1.0.0',
        },
        {
          id: 'file-ai',
          name: 'File AI',
          description: 'PDF, DOCX, Excel & More',
          icon: 'FileText',
          status: 'ready',
          version: '1.0.0',
        },
        {
          id: 'browser',
          name: 'Browser Agent',
          description: 'Web Automation & Browsing',
          icon: 'Globe',
          status: 'ready',
          version: '1.0.0',
        },
        {
          id: 'local-llm',
          name: 'Local LLM',
          description: 'Run Local AI Models',
          icon: 'Brain',
          status: 'not_loaded',
          version: '1.0.0',
        },
      ],
      setPlugins: (plugins) => set({ plugins }),
      togglePlugin: (id) => {
        set((state) => ({
          plugins: state.plugins.map((p) =>
            p.id === id
              ? { ...p, status: p.status === 'ready' ? 'not_loaded' : 'ready' }
              : p
          ),
        }));
      },

      // Navigation
      activeTab: 'home',
      setActiveTab: (tab) => set({ activeTab: tab }),

      // Expand Modes
      chatExpandMode: 'normal',
      setChatExpandMode: (mode) => set({ chatExpandMode: mode }),
      cycleExpandMode: () => {
        const modes: ('normal' | 'half' | 'full')[] = ['normal', 'half', 'full'];
        const current = get().chatExpandMode;
        const nextIndex = (modes.indexOf(current) + 1) % modes.length;
        set({ chatExpandMode: modes[nextIndex] });
      },

      // Input for chat
      input: '',
      setInput: (text) => set({ input: text }),

      // File Previews
      filePreviews: {},
      addFilePreview: (id, preview) => {
        set((state) => ({
          filePreviews: { ...state.filePreviews, [id]: preview },
        }));
      },
      removeFilePreview: (id) => {
        set((state) => {
          const { [id]: _, ...rest } = state.filePreviews;
          return { filePreviews: rest };
        });
      },

      // Memory
      todos: [],
      notes: [],
      reminders: [],
      sessions: [],
      addTodo: (todo) => {
        const newTodo: Todo = {
          ...todo,
          id: crypto.randomUUID(),
          createdAt: Date.now(),
        };
        set((state) => ({ todos: [...state.todos, newTodo] }));
      },
      toggleTodo: (id) => {
        set((state) => ({
          todos: state.todos.map((t) =>
            t.id === id ? { ...t, completed: !t.completed } : t
          ),
        }));
      },
      deleteTodo: (id) => {
        set((state) => ({
          todos: state.todos.filter((t) => t.id !== id),
        }));
      },
      addNote: (note) => {
        const newNote: Note = {
          ...note,
          id: crypto.randomUUID(),
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        set((state) => ({ notes: [...state.notes, newNote] }));
      },
      updateNote: (id, updates) => {
        set((state) => ({
          notes: state.notes.map((n) =>
            n.id === id ? { ...n, ...updates, updatedAt: Date.now() } : n
          ),
        }));
      },
      deleteNote: (id) => {
        set((state) => ({
          notes: state.notes.filter((n) => n.id !== id),
        }));
      },
      addReminder: (reminder) => {
        const newReminder: Reminder = {
          ...reminder,
          id: crypto.randomUUID(),
        };
        set((state) => ({ reminders: [...state.reminders, newReminder] }));
      },
      deleteReminder: (id) => {
        set((state) => ({
          reminders: state.reminders.filter((r) => r.id !== id),
        }));
      },

      // Learning Progress
      learningProgress: {
        active: false,
        taskId: null,
        title: '',
        percent: 0,
        status: '',
        logs: [],
      },
      setLearningProgress: (progress) => {
        set((state) => ({
          learningProgress: { ...state.learningProgress, ...progress },
        }));
      },
      clearLearningProgress: () => {
        set({
          learningProgress: {
            active: false,
            taskId: null,
            title: '',
            percent: 0,
            status: '',
            logs: [],
          },
        });
      },

      // Shopping Progress
      shoppingProgress: {
        active: false,
        query: '',
        status: '',
        platform: '',
        resultsCount: 0,
        lastUpdate: '',
      },
      setShoppingProgress: (progress) => {
        set((state) => ({
          shoppingProgress: { ...state.shoppingProgress, ...progress },
        }));
      },
      clearShoppingProgress: () => {
        set({
          shoppingProgress: {
            active: false,
            query: '',
            status: '',
            platform: '',
            resultsCount: 0,
            lastUpdate: '',
          },
        });
      },
    }),
    {
      name: 'jarvis-storage',
      partialize: (state) => ({
        mode: state.mode,
        todos: state.todos,
        notes: state.notes,
        reminders: state.reminders,
        sessions: state.sessions,
        activeTab: state.activeTab,
        chatExpandMode: state.chatExpandMode,
      }),
    }
  )
);
