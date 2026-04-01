import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import Header from './components/Header';
import SystemStatus from './components/SystemStatus';
import QueryForm from './components/QueryForm';
import ResponseDisplay from './components/ResponseDisplay';
import QueryHistory from './components/QueryHistory';
import DocumentManager from './components/DocumentManager';
import Footer from './components/Footer';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';
const MAX_HISTORY = 20;

function App() {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const loadSystemStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/health`);
      setSystemStatus(res.data);
    } catch (err) {
      console.error('Failed to load system status:', err);
    }
  }, []);

  useEffect(() => {
    loadSystemStatus();
  }, [loadSystemStatus]);

  const handleQuery = async (requestData) => {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const endpoint = requestData.advanced
        ? `${API_BASE_URL}/api/v1/query/advanced`
        : `${API_BASE_URL}/api/v1/query`;

      const result = await axios.post(endpoint, requestData);
      setResponse(result.data);

      setHistory((prev) => {
        const entry = {
          query: requestData.query,
          confidence: result.data.confidence_score || 0,
          agent: result.data.agent_type || 'unknown',
          requestData,
        };
        const next = [entry, ...prev.filter((h) => h.query !== requestData.query)];
        return next.slice(0, MAX_HISTORY);
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred while processing your query');
    } finally {
      setLoading(false);
    }
  };

  const handleHistorySelect = (item) => {
    handleQuery(item.requestData);
  };

  const llmStatus = systemStatus?.llm_status;

  return (
    <div className="app">
      <Header llmStatus={llmStatus} />

      <div className="app-body">
        {/* Mobile sidebar toggle */}
        <button
          className="sidebar-toggle"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? 'Close' : 'Menu'}
        </button>

        {/* Sidebar */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <QueryHistory history={history} onSelect={handleHistorySelect} loading={loading} />
          <DocumentManager />
        </aside>

        {/* Main content */}
        <main className="main-content">
          {systemStatus && <SystemStatus status={systemStatus} />}

          <QueryForm onSubmit={handleQuery} loading={loading} />

          {loading && (
            <div className="loading-state">
              <span className="spinner" />
              Processing your legal query...
            </div>
          )}

          {error && (
            <div className="error-state">
              <strong>Error:</strong> {error}
            </div>
          )}

          <ResponseDisplay response={response} />

          {!response && !loading && !error && (
            <div className="empty-state">
              Enter a legal question above to get an AI-powered answer based on Indian law documents.
            </div>
          )}
        </main>
      </div>

      <Footer />
    </div>
  );
}

export default App;
