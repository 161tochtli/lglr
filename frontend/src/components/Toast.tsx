import { useState, useEffect, useCallback } from 'react';
import type { WSMessage } from '../types';

interface ToastItem {
  id: string;
  title: string;
  body: string;
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((title: string, body: string) => {
    const id = crypto.randomUUID();
    setToasts(prev => [...prev, { id, title, body }]);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const handleWSMessage = useCallback((message: WSMessage) => {
    if (message.event === 'transaction.status_changed') {
      const status = message.new_status || 'unknown';
      const txId = message.transaction_id?.slice(0, 8) || '???';
      
      addToast(
        `Transaction ${status}`,
        `${txId}... → ${status}`
      );
    }
  }, [addToast]);

  return { toasts, addToast, handleWSMessage };
}

export function ToastContainer({ toasts }: { toasts: ToastItem[] }) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map(toast => (
        <div key={toast.id} className="toast">
          <div className="toast-title">{toast.title}</div>
          <div className="toast-body">{toast.body}</div>
        </div>
      ))}
    </div>
  );
}

