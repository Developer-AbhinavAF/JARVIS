export type Mode = 'text' | 'speech';

export interface MessageAction {
  type: string;
  app?: string;
  id?: string | number;
  file_name?: string;
  filename?: string;
  expression?: string;
  path?: string;
  result?: string | number;
  url?: string;
  query?: string;
  action?: string;
  author?: string;
  word_count?: number;
  data?: any;
  [key: string]: any;
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
  intent?: string;
  intent_confidence?: number;
  tool?: string;
  verified?: boolean;
  total_ms?: number;
  imageResults?: Array<{
    source: string;
    title: string;
    description: string;
    image_url: string;
    thumbnail_url: string;
    source_url: string;
    media_type: string;
    metadata?: Record<string, any>;
  }>;
  imageGallery?: {
    source: string;
    query: string;
    results: Array<{
      source: string;
      title: string;
      description: string;
      image_url: string;
      thumbnail_url: string;
      source_url: string;
      media_type: string;
    }>;
    count: number;
  };
}

export interface SystemStats {
  cpu: {
    usage: number;
    cores: number;
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
  };
  uptime: number;
}

export type SystemStatsInput = Partial<{
  cpu: Partial<SystemStats['cpu']>;
  memory: Partial<SystemStats['memory']>;
  battery: Partial<SystemStats['battery']>;
  disk: Partial<SystemStats['disk']>;
  network: Partial<SystemStats['network']>;
  processes: Partial<SystemStats['processes']>;
  uptime: number;
}>;

export const DEFAULT_SYSTEM_STATS: SystemStats = {
  cpu: {
    usage: 0,
    cores: 4,
  },
  memory: {
    used: 0,
    total: 16 * 1024 ** 3,
    percentage: 0,
  },
  battery: {
    percentage: 100,
    isCharging: true,
  },
  disk: {
    used: 0,
    total: 512 * 1024 ** 3,
    percentage: 0,
  },
  network: {
    downloadSpeed: 0,
    uploadSpeed: 0,
    ping: 0,
  },
  processes: {
    count: 0,
  },
  uptime: 0,
};

export function normalizeSystemStats(stats?: SystemStatsInput | null): SystemStats {
  return {
    cpu: {
      ...DEFAULT_SYSTEM_STATS.cpu,
      ...(stats?.cpu ?? {}),
    },
    memory: {
      ...DEFAULT_SYSTEM_STATS.memory,
      ...(stats?.memory ?? {}),
    },
    battery: {
      ...DEFAULT_SYSTEM_STATS.battery,
      ...(stats?.battery ?? {}),
    },
    disk: {
      ...DEFAULT_SYSTEM_STATS.disk,
      ...(stats?.disk ?? {}),
    },
    network: {
      ...DEFAULT_SYSTEM_STATS.network,
      ...(stats?.network ?? {}),
    },
    processes: {
      ...DEFAULT_SYSTEM_STATS.processes,
      ...(stats?.processes ?? {}),
    },
    uptime: stats?.uptime ?? DEFAULT_SYSTEM_STATS.uptime,
  };
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
