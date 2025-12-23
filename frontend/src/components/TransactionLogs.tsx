import { useState, useEffect, useCallback } from 'react';
import type { Transaction, LogEntry } from '../types';
import { getTransactionLogs } from '../api';

interface TransactionLogsProps {
  transaction: Transaction | null;
  onProcess?: (id: string) => void;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Failed to copy:', e);
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="btn-copy"
      title="Copy to clipboard"
    >
      {copied ? '✓' : '⧉'}
    </button>
  );
}

function formatLogTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatAmount(amount: string): string {
  const num = parseFloat(amount);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(num);
}

function getEventIcon(event: string): string {
  if (event.includes('created')) return '◈';
  if (event.includes('enqueued')) return '◎';
  if (event.includes('processing_started')) return '◉';
  if (event.includes('status_changed')) return '◆';
  return '◇';
}

function getEventLabel(event: string): string {
  const labels: Record<string, string> = {
    'transaction.created': 'Created',
    'transaction.enqueued': 'Queued for processing',
    'worker.processing_started': 'Processing started',
    'transaction.status_changed': 'Status changed',
  };
  return labels[event] || event;
}

export function TransactionLogs({ transaction, onProcess }: TransactionLogsProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!transaction) {
      setLogs([]);
      return;
    }

    let cancelled = false;

    const fetchLogs = async () => {
      setIsLoading(true);
      try {
        const data = await getTransactionLogs(transaction.id);
        if (!cancelled) {
          setLogs(data);
        }
      } catch (e) {
        console.error('Failed to fetch logs:', e);
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchLogs();

    // Poll for updates every 2 seconds
    const interval = setInterval(fetchLogs, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [transaction?.id]);

  if (!transaction) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">←</div>
        <div className="empty-state-text">Select a transaction to view its timeline</div>
      </div>
    );
  }

  return (
    <div className="transaction-detail">
      {/* Transaction Summary */}
      <div className="glass-card" style={{ marginBottom: 'var(--space-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-sm)' }}>
          <span className={`transaction-status-badge ${transaction.status}`}>
            {transaction.status}
          </span>
          <div className="id-with-copy">
            <span className="transaction-full-id">{transaction.id}</span>
            <CopyButton text={transaction.id} />
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ fontSize: '1.5rem', fontWeight: '600', fontFamily: 'var(--font-mono)' }}>
            {formatAmount(transaction.monto)}
          </span>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
            {transaction.tipo}
          </span>
        </div>
        
        {transaction.status === 'pendiente' && onProcess && (
          <button
            className="btn btn-process"
            onClick={() => onProcess(transaction.id)}
            style={{ marginTop: 'var(--space-md)', width: '100%' }}
          >
            Process Transaction
          </button>
        )}
      </div>

      {/* Timeline */}
      <div className="timeline-header">
        <span style={{ fontSize: '0.6875rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-tertiary)' }}>
          Event Timeline
        </span>
      </div>

      {isLoading && logs.length === 0 ? (
        <div className="empty-state loading">
          <div className="empty-state-text">Loading events...</div>
        </div>
      ) : logs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-text">No events recorded yet</div>
        </div>
      ) : (
        <div className="timeline">
          {logs.map((entry, idx) => (
            <div key={idx} className="timeline-item">
              <div className="timeline-icon">{getEventIcon(entry.event)}</div>
              <div className="timeline-content">
                <div className="timeline-event">{getEventLabel(entry.event)}</div>
                <div className="timeline-details">
                  <span className="timeline-time">{formatLogTime(entry.timestamp)}</span>
                  <span className={`timeline-service ${entry.service}`}>{entry.service}</span>
                  {entry.old_status && entry.new_status && (
                    <span className="timeline-status-change">
                      {String(entry.old_status)} → {String(entry.new_status)}
                    </span>
                  )}
                  {entry.duration_ms && (
                    <span className="timeline-duration">{String(entry.duration_ms)}ms</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

