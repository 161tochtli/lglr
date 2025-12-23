import { useState } from 'react';
import { runWikipediaBot, RPAResponse } from '../api';

interface ErrorInfo {
  message: string;
  isQuotaError: boolean;
}

export function RPAPanel() {
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<RPAResponse | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await runWikipediaBot(searchTerm);
      setResult(response);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'RPA failed';
      const isQuotaError = message.toLowerCase().includes('quota') || message.includes('429');
      setError({ message, isQuotaError });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="rpa-panel">
      <div className="panel-intro">
        <p>RPA bot that searches Wikipedia, extracts the first paragraph, and summarizes it using OpenAI.</p>
      </div>

      <form onSubmit={handleSubmit} className="glass-card">
        <div className="form-group">
          <label className="form-label">Search Term</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g. Albert Einstein"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          className="btn"
          disabled={isLoading || !searchTerm.trim()}
          style={{ width: '100%' }}
        >
          {isLoading ? 'Running bot...' : 'Search & Summarize'}
        </button>
      </form>

      {isLoading && (
        <div className="glass-card loading-card">
          <div className="loading-spinner">◐</div>
          <p className="loading-text">Opening browser, searching Wikipedia...</p>
        </div>
      )}

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
        <div className="rpa-result fade-in">
          <div className="glass-card result-section">
            <div className="result-header">
              <span className="result-label">Wikipedia</span>
              <a 
                href={result.wikipedia_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="result-link"
              >
                Open ↗
              </a>
            </div>
            <h3 className="result-title">{result.wikipedia_title}</h3>
            <p className="result-excerpt">{result.original_paragraph.slice(0, 300)}...</p>
          </div>

          <div className="glass-card result-section">
            <div className="result-header">
              <span className="result-label">AI Summary</span>
              <span className="result-id">{result.summary_id.slice(0, 8)}...</span>
            </div>
            <p className="result-text">{result.summary}</p>
          </div>
        </div>
      )}
    </div>
  );
}

