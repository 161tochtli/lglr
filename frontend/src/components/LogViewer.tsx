import type { GroupedLogs, LogEntry } from '../types';

interface LogViewerProps {
  logs: GroupedLogs;
  isLoading?: boolean;
}

function formatLogTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 2,
  });
}

function formatCorrelationId(id: string): string {
  if (id === '-') return 'local';
  return id.slice(0, 12);
}

function getEventDetails(entry: LogEntry): string {
  const parts: string[] = [];
  
  if (entry.transaction_id) {
    parts.push(`tx:${entry.transaction_id.slice(0, 8)}`);
  }
  if (entry.old_status && entry.new_status) {
    parts.push(`${entry.old_status} → ${entry.new_status}`);
  }
  if (entry.duration_ms) {
    parts.push(`${entry.duration_ms}ms`);
  }
  if (entry.status && !entry.old_status) {
    parts.push(String(entry.status));
  }
  
  return parts.join(' • ');
}

function LogEntryRow({ entry }: { entry: LogEntry }) {
  const details = getEventDetails(entry);
  
  return (
    <div className="log-entry">
      <span className="log-time">{formatLogTime(entry.timestamp)}</span>
      <span className={`log-service ${entry.service}`}>{entry.service}</span>
      <span className="log-event">
        <span className="log-event-name">{entry.event}</span>
        {details && <span className="log-details"> {details}</span>}
      </span>
    </div>
  );
}

export function LogViewer({ logs, isLoading }: LogViewerProps) {
  const groupIds = Object.keys(logs);

  if (isLoading) {
    return (
      <div className="empty-state loading">
        <div className="empty-state-text">Loading logs...</div>
      </div>
    );
  }

  if (groupIds.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⊡</div>
        <div className="empty-state-text">No events recorded yet</div>
      </div>
    );
  }

  return (
    <div>
      {groupIds.map((requestId) => {
        const entries = logs[requestId];
        const firstEntry = entries[0];
        
        return (
          <div key={requestId} className="log-group fade-in">
            <div className="log-group-header">
              <span className="log-correlation-id">
                {formatCorrelationId(requestId)}
              </span>
              <span className="log-group-time">
                {formatLogTime(firstEntry.timestamp)}
              </span>
            </div>
            
            {entries.map((entry, idx) => (
              <LogEntryRow key={`${requestId}-${idx}`} entry={entry} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

