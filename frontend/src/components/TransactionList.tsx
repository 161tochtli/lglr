import type { Transaction } from '../types';

interface TransactionListProps {
  transactions: Transaction[];
  onProcess: (id: string) => void;
  onSelect: (tx: Transaction) => void;
  selectedId?: string;
  isLoading?: boolean;
}

function formatAmount(amount: string): string {
  const num = parseFloat(amount);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(num);
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatId(id: string): string {
  return id.slice(0, 8);
}

export function TransactionList({ transactions, onProcess, onSelect, selectedId, isLoading }: TransactionListProps) {
  if (isLoading) {
    return (
      <div className="empty-state loading">
        <div className="empty-state-text">Loading transactions...</div>
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◇</div>
        <div className="empty-state-text">No transactions yet</div>
      </div>
    );
  }

  return (
    <div>
      {transactions.map((tx) => (
        <div
          key={tx.id}
          className={`glass-card transaction-card fade-in ${selectedId === tx.id ? 'selected' : ''}`}
          onClick={() => onSelect(tx)}
          style={{ cursor: 'pointer' }}
        >
          <div className={`transaction-status ${tx.status}`} title={tx.status} />
          
          <div className="transaction-info">
            <div className="transaction-id">{formatId(tx.id)}</div>
            <div className="transaction-type">{tx.tipo}</div>
          </div>
          
          <div>
            <div className="transaction-amount">{formatAmount(tx.monto)}</div>
            <div className="transaction-time">{formatTime(tx.created_at)}</div>
            
            {tx.status === 'pendiente' && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onProcess(tx.id);
                }}
                style={{ marginTop: '4px', width: '100%' }}
              >
                Process
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

