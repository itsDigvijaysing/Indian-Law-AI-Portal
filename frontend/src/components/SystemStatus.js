import React from 'react';
import './SystemStatus.css';

function SystemStatus({ status }) {
  if (!status) return null;

  return (
    <div className="system-status">
      <h3>System Status</h3>
      <div className="status-grid">
        <div className="status-item">
          <div className="status-value">
            {status.status === 'healthy' ? '\u2705' : '\u26A0\uFE0F'}
          </div>
          <div className="status-label">System</div>
        </div>
        <div className="status-item">
          <div className="status-value">{status.total_documents}</div>
          <div className="status-label">Documents</div>
        </div>
        <div className="status-item">
          <div className="status-value">{status.available_agents}</div>
          <div className="status-label">AI Agents</div>
        </div>
        <div className="status-item">
          <div className="status-value">
            {status.ai_service_initialized ? '\u2705' : '\u274C'}
          </div>
          <div className="status-label">AI Service</div>
        </div>
      </div>
    </div>
  );
}

export default SystemStatus;
