import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface UseApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
}

export function useApi<T>() {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(async (endpoint: string, options: UseApiOptions = {}) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: options.method || 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, request };
}

// Specific API hooks
export function useChat() {
  const { request, loading, error } = useApi<{ response: string }>();

  const sendMessage = useCallback(async (message: string) => {
    return request('/api/chat', {
      method: 'POST',
      body: { message },
    });
  }, [request]);

  return { sendMessage, loading, error };
}

export function useSystemStats() {
  const { request, data, loading } = useApi<{ stats: import('@/types').SystemStats }>();

  const fetchStats = useCallback(() => {
    return request('/api/system-stats');
  }, [request]);

  return { stats: data?.stats, loading, fetchStats };
}

export function useExecuteCommand() {
  const { request, loading, error } = useApi<{ result: string; success: boolean }>();

  const execute = useCallback(async (command: string, params?: Record<string, unknown>) => {
    return request('/api/execute', {
      method: 'POST',
      body: { command, params },
    });
  }, [request]);

  return { execute, loading, error };
}
