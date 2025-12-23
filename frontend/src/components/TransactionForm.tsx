import { useState } from 'react';
import type { NewTransaction, TransactionType } from '../types';

interface TransactionFormProps {
  onSubmit: (data: NewTransaction) => Promise<void>;
  disabled?: boolean;
}

export function TransactionForm({ onSubmit, disabled }: TransactionFormProps) {
  const [monto, setMonto] = useState('');
  const [tipo, setTipo] = useState<TransactionType>('ingreso');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!monto || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        user_id: crypto.randomUUID(),
        monto,
        tipo,
      });
      setMonto('');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="glass-card form-card">
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Amount</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            className="form-input"
            placeholder="0.00"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            disabled={disabled || isSubmitting}
            required
          />
        </div>
        <div className="form-group">
          <label className="form-label">Type</label>
          <select
            className="form-select"
            value={tipo}
            onChange={(e) => setTipo(e.target.value as TransactionType)}
            disabled={disabled || isSubmitting}
          >
            <option value="ingreso">Ingreso</option>
            <option value="egreso">Egreso</option>
          </select>
        </div>
      </div>
      <button
        type="submit"
        className="btn"
        disabled={disabled || isSubmitting || !monto}
        style={{ width: '100%' }}
      >
        {isSubmitting ? 'Creating...' : 'Create Transaction'}
      </button>
    </form>
  );
}

