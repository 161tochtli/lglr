import { useCallback, useState, useMemo } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useTransactions } from './hooks/useTransactions';
import { useToast, ToastContainer } from './components/Toast';
import { TransactionForm } from './components/TransactionForm';
import { TransactionList } from './components/TransactionList';
import { TransactionLogs } from './components/TransactionLogs';
import { OpenAIPanel } from './components/OpenAIPanel';
import { RPAPanel } from './components/RPAPanel';
import type { Transaction, WSMessage } from './types';

type Section = 'transactions' | 'openai' | 'rpa';

function App() {
  const { transactions, isLoading: txLoading, create, process, handleWSMessage } = useTransactions();
  const { toasts, handleWSMessage: toastHandler } = useToast();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<Section>('transactions');

  // Get the selected transaction from the list (to reflect status updates)
  const selectedTransaction = useMemo(() => {
    if (!selectedId) return null;
    return transactions.find(tx => tx.id === selectedId) || null;
  }, [selectedId, transactions]);

  // Combined WebSocket message handler
  const onWSMessage = useCallback((message: WSMessage) => {
    handleWSMessage(message);
    toastHandler(message);
  }, [handleWSMessage, toastHandler]);

  useWebSocket('/ws/transactions/stream', {
    onMessage: onWSMessage,
  });

  const handleCreate = async (data: Parameters<typeof create>[0]) => {
    const tx = await create(data);
    setSelectedId(tx.id);
  };

  const handleProcess = async (id: string) => {
    await process(id);
  };

  const handleSelect = (tx: Transaction) => {
    setSelectedId(tx.id);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Lglr</h1>
        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeSection === 'transactions' ? 'active' : ''}`}
            onClick={() => setActiveSection('transactions')}
          >
            Transactions
          </button>
          <button
            className={`nav-tab ${activeSection === 'rpa' ? 'active' : ''}`}
            onClick={() => setActiveSection('rpa')}
          >
            RPA
          </button>
          <button
            className={`nav-tab ${activeSection === 'openai' ? 'active' : ''}`}
            onClick={() => setActiveSection('openai')}
          >
            Summarize
          </button>
        </nav>
      </header>

      {activeSection === 'transactions' && (
        <main className="main-content">
          {/* Left Panel: Transactions */}
          <section className="panel">
            <div className="panel-header">
              <h2 className="panel-title">Total Transactions</h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {transactions.length} total
              </span>
            </div>
            <div className="panel-content">
              <TransactionForm onSubmit={handleCreate} />
              <TransactionList
                transactions={transactions}
                onProcess={handleProcess}
                onSelect={handleSelect}
                selectedId={selectedTransaction?.id}
                isLoading={txLoading}
              />
            </div>
          </section>

          {/* Right Panel: Transaction Detail */}
          <section className="panel">
            <div className="panel-header">
              <h2 className="panel-title">Details</h2>
              {selectedTransaction && (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => setSelectedId(null)}
                >
                  Clear
                </button>
              )}
            </div>
            <div className="panel-content">
              <TransactionLogs transaction={selectedTransaction} onProcess={handleProcess} />
            </div>
          </section>
        </main>
      )}

      {activeSection === 'openai' && (
        <main className="main-content single-panel">
          <section className="panel panel-wide">
            <div className="panel-header">
              <h2 className="panel-title">OpenAI Summarization</h2>
            </div>
            <div className="panel-content">
              <OpenAIPanel />
            </div>
          </section>
        </main>
      )}

      {activeSection === 'rpa' && (
        <main className="main-content single-panel">
          <section className="panel panel-wide">
            <div className="panel-header">
              <h2 className="panel-title">Wikipedia RPA Bot</h2>
            </div>
            <div className="panel-content">
              <RPAPanel />
            </div>
          </section>
        </main>
      )}

      <ToastContainer toasts={toasts} />
    </div>
  );
}

export default App;
