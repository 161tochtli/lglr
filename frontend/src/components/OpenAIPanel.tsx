import { useState } from 'react';
import { summarizeText, SummaryResponse } from '../api';

interface ErrorInfo {
  message: string;
  isQuotaError: boolean;
}

export function OpenAIPanel() {
  const [text, setText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await summarizeText(text);
      setResult(response);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to summarize';
      const isQuotaError = message.toLowerCase().includes('quota') || message.includes('429');
      setError({ message, isQuotaError });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="openai-panel">
      <div className="panel-intro">
        <p>Send text to OpenAI for summarization. The API will generate a concise summary of your input.</p>
      </div>

      <form onSubmit={handleSubmit} className="glass-card">
        <div className="form-group">
          <label className="form-label">Text to Summarize</label>
          <textarea
            className="form-textarea"
            placeholder="Enter text to summarize..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          className="btn"
          disabled={isLoading || !text.trim()}
          style={{ width: '100%' }}
        >
          {isLoading ? 'Summarizing...' : 'Summarize'}
        </button>
      </form>

      {error && (
        <div className={`glass-card error-card ${error.isQuotaError ? 'quota-error' : ''}`}>
          {error.isQuotaError ? (
            <div className="quota-error-content">
              <div className="quota-error-icon">⚠</div>
              <div className="quota-error-text">
                <strong>OpenAI Quota Exceeded</strong>
                <p>Your API key has no credits remaining. Add funds at <a href="https://platform.openai.com/account/billing" target="_blank" rel="noopener noreferrer">OpenAI Billing</a> or switch to stub mode.</p>
              </div>
            </div>
          ) : (
            <span className="error-text">{error.message}</span>
          )}
        </div>
      )}

      {result && (
        <div className="result-card glass-card fade-in">
          <div className="result-header">
            <span className="result-label">Summary</span>
            <span className="result-id">{result.id.slice(0, 8)}...</span>
          </div>
          <p className="result-text">{result.summary}</p>
          {result.model && (
            <div className="result-meta">
              <span>Model: {result.model}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

