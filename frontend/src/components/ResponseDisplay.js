import React from 'react';
import ReactMarkdown from 'react-markdown';
import './ResponseDisplay.css';

function ResponseDisplay({ response }) {
  if (!response) return null;

  return (
    <div className="response-display">
      <h3>Legal Answer</h3>

      <div className="response-content">
        <ReactMarkdown>{response.answer}</ReactMarkdown>
      </div>

      <div className="response-meta">
        <span className="meta-item">
          <strong>Agent:</strong> {response.agent_type}
        </span>
        <span className={`meta-item confidence ${getConfidenceClass(response.confidence_score)}`}>
          <strong>Confidence:</strong> {(response.confidence_score * 100).toFixed(1)}%
        </span>
        {response.processing_time_ms && (
          <span className="meta-item">
            <strong>Time:</strong> {response.processing_time_ms.toFixed(0)}ms
          </span>
        )}
        {response.retrieved_documents != null && (
          <span className="meta-item">
            <strong>Docs Searched:</strong> {response.retrieved_documents}
          </span>
        )}
      </div>

      {response.retrieval_sources && response.retrieval_sources.length > 0 && (
        <div className="sources-panel">
          <h4>Retrieval Sources</h4>
          {response.retrieval_sources.map((source, index) => (
            <div key={index} className="source-item">
              <div className="source-header">
                <span className="source-doc-badge">{formatDocName(source.document)}</span>
                <span className="source-section">{source.section}</span>
              </div>
              <div className="source-scores">
                <div className="score-bar">
                  <span className="score-label">Similarity</span>
                  <div className="score-track">
                    <div className="score-fill" style={{ width: `${(source.similarity_score || 0) * 100}%` }} />
                  </div>
                  <span className="score-value">{((source.similarity_score || 0) * 100).toFixed(0)}%</span>
                </div>
                {source.fusion_score != null && source.fusion_score > 0 && (
                  <div className="score-bar">
                    <span className="score-label">Fusion</span>
                    <div className="score-track fusion">
                      <div className="score-fill fusion" style={{ width: `${Math.min((source.fusion_score || 0) * 200, 100)}%` }} />
                    </div>
                    <span className="score-value">{source.fusion_score.toFixed(3)}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {response.sources && response.sources.length > 0 && (
        <div className="legal-refs">
          <h4>Legal References</h4>
          <ul>
            {response.sources.map((source, index) => (
              <li key={index}>{source}</li>
            ))}
          </ul>
        </div>
      )}

      {response.reasoning_steps && response.reasoning_steps.length > 0 && (
        <div className="reasoning">
          <h4>AI Reasoning Process</h4>
          <ol>
            {response.reasoning_steps.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {response.reformulated_queries && (
        <div className="fusion-details">
          <h4>RAG Fusion - Query Reformulations</h4>
          <ul>
            {response.reformulated_queries.map((q, index) => (
              <li key={index}>{q}</li>
            ))}
          </ul>
          {response.fusion_statistics && (
            <div className="fusion-stats">
              <span>Unique results: {response.fusion_statistics.total_unique_results}</span>
              <span>Avg coverage: {response.fusion_statistics.average_query_coverage?.toFixed(1)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function getConfidenceClass(score) {
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

function formatDocName(name) {
  return (name || 'Unknown').replace(/_/g, ' ').replace(/\d{4}$/, '').trim();
}

export default ResponseDisplay;
