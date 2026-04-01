import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './DocumentManager.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

function DocumentManager() {
  const [documents, setDocuments] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState(null);

  const loadDocuments = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/v1/admin/documents`);
      setDocuments(res.data.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleProcessAll = async () => {
    setProcessing(true);
    setMessage(null);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/v1/admin/process-documents`);
      setMessage({ type: 'success', text: `Processed ${res.data.documents_processed || 0} documents` });
      await loadDocuments();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Processing failed' });
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="document-manager">
      <div className="dm-header">
        <h4>Documents</h4>
        <button
          className="dm-process-btn"
          onClick={handleProcessAll}
          disabled={processing}
        >
          {processing ? 'Processing...' : 'Re-process All'}
        </button>
      </div>

      {message && (
        <div className={`dm-message ${message.type}`}>{message.text}</div>
      )}

      {documents.length > 0 ? (
        <ul className="dm-list">
          {documents.map((doc, index) => (
            <li key={index} className="dm-item">
              <span className="dm-icon">PDF</span>
              <span className="dm-name">{formatName(doc.name || doc)}</span>
              {doc.chunks != null && (
                <span className="dm-chunks">{doc.chunks} chunks</span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="dm-empty">No documents ingested yet</p>
      )}
    </div>
  );
}

function formatName(name) {
  return name.replace(/_/g, ' ').replace(/\.pdf$/i, '');
}

export default DocumentManager;
