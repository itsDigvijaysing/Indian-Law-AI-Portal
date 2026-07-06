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
      const res = await axios.get(`${API_BASE_URL}/api/v1/admin/documents/list`);
      setDocuments(res.data.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
      setMessage({ type: 'error', text: 'Failed to load document list' });
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleProcessAll = async () => {
    setProcessing(true);
    setMessage(null);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/v1/admin/documents/process`, {
        file_paths: documents.map((doc) => doc.filename),
      });
      const processed = res.data.processed?.length || 0;
      const skipped = res.data.skipped?.length || 0;
      const failed = res.data.failed?.length || 0;
      setMessage({
        type: failed > 0 ? 'error' : 'success',
        text: `Processed ${processed}, skipped ${skipped} already ingested` +
          (failed ? `, ${failed} FAILED` : '') +
          (res.data.total_chunks ? `, ${res.data.total_chunks} new chunks` : ''),
      });
      await loadDocuments();
    } catch (err) {
      const detail = err.response?.data?.detail ?? err.response?.data?.error;
      setMessage({ type: 'error', text: (typeof detail === 'string' && detail) || 'Processing failed' });
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="rail-section">
      <details className="dm">
        <summary className="dm-summary">
          <span className="rail-title dm-title">Corpus</span>
          <span className="dm-count">{documents.length}</span>
        </summary>

        {message && <div className={`dm-message ${message.type}`}>{message.text}</div>}

        {documents.length > 0 ? (
          <ul className="dm-list">
            {documents.map((doc, index) => (
              <li key={index} className="dm-item" title={formatName(doc.filename)}>
                <span className="dm-dot" />
                <span className="dm-name">{formatName(doc.filename)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="dm-empty">No documents found</p>
        )}

        <button
          className="dm-ingest"
          onClick={handleProcessAll}
          disabled={processing || documents.length === 0}
        >
          {processing ? 'Processing…' : 'Ingest new documents'}
        </button>
      </details>
    </div>
  );
}

function formatName(name) {
  return (name || '').replace(/_/g, ' ').replace(/\.pdf$/i, '');
}

export default DocumentManager;
