import React from 'react';
import './QueryHistory.css';

function QueryHistory({ history, onSelect, loading }) {
  if (history.length === 0) return null;

  return (
    <div className="query-history">
      <h4>Recent Queries</h4>
      <ul className="history-list">
        {history.map((item, index) => (
          <li key={index} className="history-item">
            <button
              className="history-btn"
              onClick={() => onSelect(item)}
              disabled={loading}
              title={item.query}
            >
              <span className="history-query">{item.query}</span>
              <span className="history-meta">
                <span className={`history-confidence ${getConfClass(item.confidence)}`}>
                  {(item.confidence * 100).toFixed(0)}%
                </span>
                <span className="history-agent">{item.agent}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function getConfClass(score) {
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

export default QueryHistory;
