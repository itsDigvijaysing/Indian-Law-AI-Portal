import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './ResponseDisplay.css';

// Turn validated [n] markers into markdown links the CitationAnchor renders as chips.
// Only 1-2 digit numbers: bracketed years in legal text ("[1963]") are literals.
function linkifyCitations(answer) {
  return (answer || '').replace(/\[(\d{1,2})\](?!\()/g, '[$1](#cite-$1)');
}

function CitationAnchor({ href, children, node, ...props }) {
  if (href && href.startsWith('#cite-')) {
    const n = href.slice('#cite-'.length);
    const onClick = (e) => {
      e.preventDefault();
      const card = document.getElementById(`source-card-${n}`);
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.classList.remove('flash');
        void card.offsetWidth;
        card.classList.add('flash');
      }
    };
    return (
      <sup className="citation-chip" onClick={onClick} role="link" tabIndex={0}
           onKeyDown={(e) => e.key === 'Enter' && onClick(e)}>
        {n}
      </sup>
    );
  }
  return <a href={href} target="_blank" rel="noreferrer" {...props}>{children}</a>;
}

function EraTag({ era }) {
  if (era === 'pre-2024') return <span className="tag legacy">legacy</span>;
  if (era === 'post-2024') return <span className="tag current">current</span>;
  return null;
}

function SourceCard({ source, streaming }) {
  const pages = source.page_start
    ? (source.page_start === source.page_end ? `p. ${source.page_start}` : `pp. ${source.page_start}-${source.page_end}`)
    : null;
  const stateClass = source.cited ? 'cited' : (streaming ? '' : 'uncited');
  return (
    <div id={source.id != null ? `source-card-${source.id}` : undefined}
         className={`source-card ${stateClass}`}>
      <div className="source-top">
        {source.id != null && <span className="source-num">{source.id}</span>}
        <span className="source-title">{source.document_title || formatDocName(source.document)}</span>
        <EraTag era={source.era} />
      </div>
      <div className="source-ref">
        <span className="source-section">{source.section}</span>
        {pages && <span className="source-pages"> · {pages}</span>}
      </div>
      {source.snippet && <p className="source-snippet">{source.snippet}…</p>}
    </div>
  );
}

function confidenceLabel(score) {
  if (score >= 0.7) return 'High';
  if (score >= 0.4) return 'Medium';
  return 'Low';
}
function confidenceClass(score) {
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

function ResponseDisplay({ response }) {
  const [showDetails, setShowDetails] = useState(false);
  if (!response) return null;

  const sources = response.retrieval_sources || [];
  const cited = response.streaming ? sources : sources.filter((s) => s.cited);
  const uncited = response.streaming ? [] : sources.filter((s) => !s.cited);
  const isAssistant = response.agent_type === 'Assistant';
  const hasSources = sources.length > 0;

  return (
    <article className={`answer ${hasSources ? 'answer-grid' : ''}`}>
      <div className="answer-main">
        {/* Quiet meta line above the answer */}
        <div className="answer-meta">
          {response.detected_category && (
            <span className="meta-chip">{response.detected_category}</span>
          )}
          {response.streaming ? (
            <span className="meta-muted"><span className="live-dot" /> Answering…</span>
          ) : !isAssistant && (
            <span className={`meta-conf ${confidenceClass(response.confidence_score || 0)}`}>
              {confidenceLabel(response.confidence_score || 0)} confidence
              <span className="conf-pct">{((response.confidence_score || 0) * 100).toFixed(0)}%</span>
            </span>
          )}
          {response.retrieved_documents != null && !isAssistant && (
            <span className="meta-muted">{response.retrieved_documents} passages</span>
          )}
          {response.processing_time_ms != null && (
            <span className="meta-muted">{(response.processing_time_ms / 1000).toFixed(1)}s</span>
          )}
        </div>

        <div className="answer-body">
          <ReactMarkdown components={{ a: CitationAnchor }}>
            {linkifyCitations(response.answer)}
          </ReactMarkdown>
          {response.streaming && <span className="caret" />}
        </div>

        {(response.reasoning_steps?.length > 0 || response.reformulated_queries?.length > 0) && (
          <div className="details-block">
            <button className="details-toggle" onClick={() => setShowDetails((v) => !v)}>
              {showDetails ? 'Hide' : 'Show'} retrieval details
            </button>
            {showDetails && (
              <div className="details-content">
                {response.reasoning_steps?.length > 0 && (
                  <div>
                    <h4>Reasoning</h4>
                    <ol>{response.reasoning_steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
                  </div>
                )}
                {response.reformulated_queries?.length > 0 && (
                  <div>
                    <h4>Query reformulations</h4>
                    <ul>{response.reformulated_queries.map((q, i) => <li key={i}>{q}</li>)}</ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {hasSources && (
        <aside className="answer-side">
          <h3 className="sources-title">
            Sources <span className="sources-count">{cited.length || sources.length}</span>
          </h3>
          <div className="sources-list">
            {(cited.length > 0 ? cited : []).map((s) => (
              <SourceCard key={s.id ?? s.section} source={s} streaming={response.streaming} />
            ))}
          </div>
          {cited.length === 0 && !response.streaming && (
            <p className="sources-none">No specific sources cited.</p>
          )}
          {uncited.length > 0 && (
            <details className="also">
              <summary>Also retrieved ({uncited.length})</summary>
              <div className="sources-list">
                {uncited.map((s, i) => <SourceCard key={s.id ?? `u${i}`} source={s} />)}
              </div>
            </details>
          )}
        </aside>
      )}
    </article>
  );
}

function formatDocName(name) {
  return (name || 'Unknown').replace(/_/g, ' ').replace(/\d{4}$/, '').trim();
}

export default ResponseDisplay;
