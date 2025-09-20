import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

function App() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);

  // Load system status on component mount
  useEffect(() => {
    loadSystemStatus();
  }, []);

  const loadSystemStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setSystemStatus(response.data);
    } catch (err) {
      console.error('Failed to load system status:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const requestData = {
        query: query.trim(),
        include_sources: true,
        max_results: 10
      };

      const result = await axios.post(`${API_BASE_URL}/api/v1/query`, requestData);
      setResponse(result.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred while processing your query');
      console.error('Query error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExampleQuery = (exampleQuery) => {
    setQuery(exampleQuery);
  };

  const exampleQueries = [
    "What is the punishment for theft under IPC?",
    "What are the fundamental rights under the Constitution?",
    "How to file a civil suit under CPC?",
    "What is the procedure for bail in criminal cases?"
  ];

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <h1>Indian Law AI Portal</h1>
        <p>AI-powered legal query assistant for Indian laws</p>
      </header>

      {/* System Status */}
      {systemStatus && (
        <div className="system-status">
          <h3>System Status</h3>
          <div className="status-grid">
            <div className="status-item">
              <div className="status-value">
                {systemStatus.status === 'healthy' ? '✅' : '⚠️'}
              </div>
              <div className="status-label">System Status</div>
            </div>
            <div className="status-item">
              <div className="status-value">{systemStatus.total_documents}</div>
              <div className="status-label">Documents Loaded</div>
            </div>
            <div className="status-item">
              <div className="status-value">{systemStatus.available_agents}</div>
              <div className="status-label">AI Agents</div>
            </div>
            <div className="status-item">
              <div className="status-value">
                {systemStatus.ai_service_initialized ? '✅' : '❌'}
              </div>
              <div className="status-label">AI Service</div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="main-content">
        {/* Query Section */}
        <div className="query-section">
          <h2>Ask a Legal Question</h2>
          
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="query">Your Legal Query:</label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your legal question here... For example: 'What is the punishment for theft under IPC?'"
                disabled={loading}
              />
            </div>
            
            <button type="submit" className="btn" disabled={loading || !query.trim()}>
              {loading ? (
                <span className="loading">
                  <span className="spinner"></span>
                  Processing...
                </span>
              ) : (
                'Get Legal Answer'
              )}
            </button>
          </form>

          {/* Example Queries */}
          <div style={{ marginTop: '2rem' }}>
            <h4>Example Queries:</h4>
            {exampleQueries.map((example, index) => (
              <button
                key={index}
                onClick={() => handleExampleQuery(example)}
                style={{
                  display: 'block',
                  width: '100%',
                  margin: '0.5rem 0',
                  padding: '0.8rem',
                  background: '#f8f9fa',
                  border: '1px solid #e9ecef',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background-color 0.2s'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#e9ecef'}
                onMouseLeave={(e) => e.target.style.backgroundColor = '#f8f9fa'}
                disabled={loading}
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        {/* Response Section */}
        <div className="response-section">
          <h2>AI Response</h2>
          
          {loading && (
            <div className="loading">
              <span className="spinner"></span>
              Processing your legal query...
            </div>
          )}

          {error && (
            <div className="error">
              <strong>Error:</strong> {error}
            </div>
          )}

          {response && (
            <div className="response">
              <h3>Legal Answer:</h3>
              <div className="response-content">
                {response.answer}
              </div>

              <div className="response-meta">
                <span className="meta-item">
                  <strong>Agent:</strong> {response.agent_type}
                </span>
                <span className="meta-item">
                  <strong>Confidence:</strong> {(response.confidence_score * 100).toFixed(1)}%
                </span>
                {response.processing_time_ms && (
                  <span className="meta-item">
                    <strong>Processing Time:</strong> {response.processing_time_ms.toFixed(0)}ms
                  </span>
                )}
                {response.retrieved_documents && (
                  <span className="meta-item">
                    <strong>Documents Searched:</strong> {response.retrieved_documents}
                  </span>
                )}
              </div>

              {response.sources && response.sources.length > 0 && (
                <div className="sources">
                  <h4>Legal References:</h4>
                  <ul>
                    {response.sources.map((source, index) => (
                      <li key={index}>{source}</li>
                    ))}
                  </ul>
                </div>
              )}

              {response.reasoning_steps && response.reasoning_steps.length > 0 && (
                <div className="sources">
                  <h4>AI Reasoning Process:</h4>
                  <ul>
                    {response.reasoning_steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {!response && !loading && !error && (
            <div style={{ color: '#666', fontStyle: 'italic', textAlign: 'center', padding: '2rem' }}>
              Enter a legal question above to get an AI-powered answer based on Indian law documents.
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer style={{ textAlign: 'center', padding: '2rem 0', color: '#666', borderTop: '1px solid #eee', marginTop: '2rem' }}>
        <p>Indian Law AI Portal - Powered by Agent Development Kit & RAG Fusion</p>
        <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
          <strong>Note:</strong> This is an AI assistant. Please consult qualified legal professionals for official legal advice.
        </p>
      </footer>
    </div>
  );
}

export default App;