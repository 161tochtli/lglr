// ═══════════════════════════════════════════════════════════════════════════
// Domain Types
// ═══════════════════════════════════════════════════════════════════════════

export type TransactionType = 'ingreso' | 'egreso';
export type TransactionStatus = 'pendiente' | 'procesado' | 'fallido' | 'cancelado';

export interface Transaction {
  id: string;
  user_id: string;
  monto: string;
  tipo: TransactionType;
  status: TransactionStatus;
  created_at: string;
  updated_at: string;
}

export interface NewTransaction {
  user_id: string;
  monto: string;
  tipo: TransactionType;
}

// ═══════════════════════════════════════════════════════════════════════════
// Log Types
// ═══════════════════════════════════════════════════════════════════════════

export interface LogEntry {
  timestamp: string;
  level: string;
  service: string;
  event: string;
  request_id: string;
  transaction_id?: string;
  job_id?: string;
  [key: string]: unknown;
}

export type GroupedLogs = Record<string, LogEntry[]>;

// ═══════════════════════════════════════════════════════════════════════════
// WebSocket Types
// ═══════════════════════════════════════════════════════════════════════════

export interface WSMessage {
  event: string;
  transaction_id?: string;
  old_status?: TransactionStatus;
  new_status?: TransactionStatus;
  timestamp?: string;
  type?: 'keepalive';
}

