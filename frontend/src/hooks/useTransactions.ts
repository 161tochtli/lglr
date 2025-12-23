import { useState, useEffect, useCallback } from 'react';
import type { Transaction, NewTransaction, WSMessage } from '../types';
import { listTransactions, createTransaction, processTransaction } from '../api';

interface UseTransactionsReturn {
  transactions: Transaction[];
  isLoading: boolean;
  error: string | null;
  create: (data: NewTransaction) => Promise<Transaction>;
  process: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
  handleWSMessage: (message: WSMessage) => void;
}

export function useTransactions(): UseTransactionsReturn {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await listTransactions();
      setTransactions(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load transactions');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const create = useCallback(async (data: NewTransaction): Promise<Transaction> => {
    const tx = await createTransaction(data);
    setTransactions(prev => [tx, ...prev]);
    return tx;
  }, []);

  const process = useCallback(async (id: string): Promise<void> => {
    await processTransaction(id);
    // The status will update via WebSocket
  }, []);

  const handleWSMessage = useCallback((message: WSMessage) => {
    if (message.event === 'transaction.status_changed' && message.transaction_id) {
      setTransactions(prev =>
        prev.map(tx =>
          tx.id === message.transaction_id && message.new_status
            ? { ...tx, status: message.new_status, updated_at: message.timestamp || tx.updated_at }
            : tx
        )
      );
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    transactions,
    isLoading,
    error,
    create,
    process,
    refresh,
    handleWSMessage,
  };
}

