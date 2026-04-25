export type Mode = 'text' | 'speech';

export interface MessageAction {
  type: string;
  app?: string;
  path?: string;
  url?: string;
  query?: string;
  action?: string;
  data?: any;
}

export interface MessageActions {
  copy?: boolean;
  speak?: boolean;
  delete?: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  actions?: MessageActions;
  actionButtons?: MessageAction[];
}

export interface SystemStats {
  cpu: {
    usage: number;
    cores: number;
    frequency: number;
  };
  memory: {
    used: number;
    total: number;
    percentage: number;
  };
  battery: {
    percentage: number;
    isCharging: boolean;
    timeRemaining?: number;
  };
  disk: {
    used: number;
    total: number;
    percentage: number;
  };
  network: {
    downloadSpeed: number;
    uploadSpeed: number;
    ping: number;
  };
  processes: {
    count: number;
    top: Array<{ name: string; cpu: number; memory: number }>;
  };
  uptime: number;
}

export interface Plugin {
  id: string;
  name: string;
  description: string;
  icon: string;
  status: 'ready' | 'loading' | 'error' | 'not_loaded';
  version: string;
}

export interface NavItem {
  id: string;
  label: string;
  icon: string;
  badge?: string;
}

export interface QuickAction {
  id: string;
  label: string;
  icon: string;
  description: string;
}

export interface Todo {
  id: string;
  text: string;
  completed: boolean;
  priority: 'low' | 'medium' | 'high';
  createdAt: number;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  createdAt: number;
  updatedAt: number;
}

export interface Reminder {
  id: string;
  text: string;
  time: number;
  completed?: boolean;
  repeat?: 'daily' | 'weekly' | 'monthly';
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}
