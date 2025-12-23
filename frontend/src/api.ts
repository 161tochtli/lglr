// ═══════════════════════════════════════════════════════════════════════════
// API Client
// ═══════════════════════════════════════════════════════════════════════════

import type { Transaction, NewTransaction, LogEntry, GroupedLogs } from './types';

const API_BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // Extract headers separately to merge them correctly
  const { headers: optionsHeaders, ...restOptions } = options || {};
  
  const response = await fetch(`${API_BASE}${path}`, {
    ...restOptions,
    headers: {
      'Content-Type': 'application/json',
      ...optionsHeaders,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }

  return response.json();
}

// ═══════════════════════════════════════════════════════════════════════════
// Transactions
// ═══════════════════════════════════════════════════════════════════════════

export async function listTransactions(limit = 50): Promise<Transaction[]> {
  return request<Transaction[]>(`/transactions?limit=${limit}`);
}

export async function createTransaction(data: NewTransaction): Promise<Transaction> {
  // Generate idempotency key for safe retries (standard pattern: client generates the key)
  const idempotencyKey = crypto.randomUUID();
  
  return request<Transaction>('/transactions/create', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {
      'Idempotency-Key': idempotencyKey,
    },
  });
}

export async function processTransaction(transactionId: string): Promise<{ job_id: string }> {
  return request<{ job_id: string }>(`/transactions/async-process?transaction_id=${transactionId}`, {
    method: 'POST',
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// Logs
// ═══════════════════════════════════════════════════════════════════════════

export async function listLogs(limit = 100): Promise<LogEntry[]> {
  return request<LogEntry[]>(`/logs?limit=${limit}`);
}

export async function listLogsGrouped(limit = 50): Promise<GroupedLogs> {
  return request<GroupedLogs>(`/logs/grouped?limit=${limit}`);
}

export async function getTransactionLogs(transactionId: string): Promise<LogEntry[]> {
  return request<LogEntry[]>(`/logs/transaction/${transactionId}`);
}

// ═══════════════════════════════════════════════════════════════════════════
// OpenAI / Summarize
// ═══════════════════════════════════════════════════════════════════════════

export interface SummaryResponse {
  id: string;
  text: string;
  summary: string;
  created_at: string;
  model: string | null;
  request_id: string | null;
}

export async function summarizeText(text: string): Promise<SummaryResponse> {
  return request<SummaryResponse>('/assistant/summarize', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// RPA / Wikipedia Bot
// ═══════════════════════════════════════════════════════════════════════════

export interface RPAResponse {
  search_term: string;
  wikipedia_title: string;
  wikipedia_url: string;
  original_paragraph: string;
  summary: string;
  summary_id: string;
}

export async function runWikipediaBot(searchTerm: string): Promise<RPAResponse> {
  return request<RPAResponse>('/rpa/wikipedia-summarize', {
    method: 'POST',
    body: JSON.stringify({ search_term: searchTerm }),
  });
}

