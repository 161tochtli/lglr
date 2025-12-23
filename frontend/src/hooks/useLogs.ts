import { useState, useEffect, useCallback } from 'react';
import type { GroupedLogs } from '../types';
import { listLogsGrouped } from '../api';

interface UseLogsReturn {
  logs: GroupedLogs;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useLogs(pollInterval = 2000): UseLogsReturn {
  const [logs, setLogs] = useState<GroupedLogs>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await listLogsGrouped();
      setLogs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load logs');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();

    // Poll for updates
    const interval = setInterval(refresh, pollInterval);
    return () => clearInterval(interval);
  }, [refresh, pollInterval]);

  return { logs, isLoading, error, refresh };
}

