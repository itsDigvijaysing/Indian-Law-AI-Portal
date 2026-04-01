import React, { useState } from 'react';
import './QueryForm.css';

const EXAMPLE_QUERIES = [
  "What is the punishment for theft under BNS?",
  "What are the fundamental rights under the Constitution?",
  "How to file a civil suit under CPC?",
  "What is the procedure for bail under BNSS?",
  "Compare IPC Section 302 with the corresponding BNS provision",
  "What is Article 21 of the Constitution?"
];

function QueryForm({ onSubmit, loading }) {
  const [query, setQuery] = useState('');
  const [advancedMode, setAdvancedMode] = useState(false);
  const [advancedOptions, setAdvancedOptions] = useState({
    fusionQueries: 3,
    explainReasoning: false,
    confidenceThreshold: 0,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const requestData = {
      query: query.trim(),
      include_sources: true,
      max_results: 10
    };

    if (advancedMode) {
      requestData.advanced = true;
      requestData.fusion_queries = advancedOptions.fusionQueries;
      requestData.explain_reasoning = advancedOptions.explainReasoning;
      if (advancedOptions.confidenceThreshold > 0) {
        requestData.filters = {
          confidence_threshold: advancedOptions.confidenceThreshold / 100
        };
      }
    }

    onSubmit(requestData);
  };

  return (
    <div className="query-section">
      <h2>Ask a Legal Question</h2>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="query">Your Legal Query:</label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your legal question here... e.g., 'What is the punishment for theft under BNS?'"
            disabled={loading}
          />
        </div>

        <div className="query-actions">
          <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>
            {loading ? (
              <span className="loading-inline">
                <span className="spinner" />
                Processing...
              </span>
            ) : (
              'Get Legal Answer'
            )}
          </button>
          <button
            type="button"
            className={`btn btn-secondary ${advancedMode ? 'active' : ''}`}
            onClick={() => setAdvancedMode(!advancedMode)}
          >
            {advancedMode ? 'Simple Mode' : 'Advanced'}
          </button>
        </div>
      </form>

      {advancedMode && (
        <div className="advanced-options">
          <h4>Advanced Options</h4>
          <div className="option-row">
            <label>
              RAG Fusion Queries: <strong>{advancedOptions.fusionQueries}</strong>
              <input
                type="range"
                min="1"
                max="10"
                value={advancedOptions.fusionQueries}
                onChange={(e) => setAdvancedOptions({ ...advancedOptions, fusionQueries: parseInt(e.target.value) })}
              />
            </label>
          </div>
          <div className="option-row">
            <label>
              Min Confidence: <strong>{advancedOptions.confidenceThreshold}%</strong>
              <input
                type="range"
                min="0"
                max="90"
                step="10"
                value={advancedOptions.confidenceThreshold}
                onChange={(e) => setAdvancedOptions({ ...advancedOptions, confidenceThreshold: parseInt(e.target.value) })}
              />
            </label>
          </div>
          <div className="option-row">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={advancedOptions.explainReasoning}
                onChange={(e) => setAdvancedOptions({ ...advancedOptions, explainReasoning: e.target.checked })}
              />
              Show RAG Fusion reasoning details
            </label>
          </div>
        </div>
      )}

      <div className="example-queries">
        <h4>Example Queries:</h4>
        {EXAMPLE_QUERIES.map((example, index) => (
          <button
            key={index}
            className="example-btn"
            onClick={() => setQuery(example)}
            disabled={loading}
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}

export default QueryForm;
