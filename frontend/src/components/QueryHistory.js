import React from 'react';
import './QueryHistory.css';

function QueryHistory({ history, onSelect, loading }) {
  if (history.length === 0) return null;

  return (
    <nav className="rail-section">
      <div className="rail-title">Recent</div>
      <ul className="history-list">
        {history.map((item, index) => (
          <li key={index}>
            <button
              className="history-btn"
              onClick={() => onSelect(item)}
              disabled={loading}
              title={item.query}
            >
              <span className="history-query">{item.query}</span>
              <span className="history-agent">{item.agent}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export default QueryHistory;
