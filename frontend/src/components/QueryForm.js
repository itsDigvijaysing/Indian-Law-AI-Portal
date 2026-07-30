import React, { useState, useRef, useEffect } from 'react';
import './QueryForm.css';

// Plain-language questions a regular person asks — no section or article numbers.
const EXAMPLE_QUERIES = [
  'If someone’s cheque bounces, what can I do?',
  'What are the grounds for getting a divorce?',
  'Can my landlord evict me without notice?',
  'I bought a defective product. How do I get a refund?',
  'What is the punishment for murder?',
  'Can the police arrest me without a warrant?',
  'How do I file an FIR, and can the police refuse to register it?',
  'Does a daughter have equal rights in family property?',
  'My employer is not paying my salary. What can I do?',
  'What are my rights if I am facing domestic violence?',
  'How can I get bail if I fear I might be arrested?',
  'Is a spoken (verbal) agreement legally valid?',
  'What is the punishment for cheating and fraud?',
  'How do I register a marriage between two different religions?',
  'Can I claim maintenance from my spouse after separation?',
  'What can I do if someone refuses to repay money I lent them?',
  'How much time do I have to file a case over a money dispute?',
  'What are my rights over my personal data collected by companies?',
  'What is the punishment for theft?',
];

function pickExamples(n) {
  const a = [...EXAMPLE_QUERIES];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, n);
}

function QueryForm({ onSubmit, loading, home }) {
  const [query, setQuery] = useState('');
  const [advancedMode, setAdvancedMode] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advancedOptions, setAdvancedOptions] = useState({
    fusionQueries: 3,
    explainReasoning: false,
    confidenceThreshold: 0,
  });
  const taRef = useRef(null);
  const [examples] = useState(() => pickExamples(6));

  // Auto-grow the textarea to fit its content
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 220) + 'px';
  }, [query]);

  const submit = () => {
    if (!query.trim() || loading) return;
    const requestData = { query: query.trim(), include_sources: true, max_results: 10 };
    if (advancedMode) {
      requestData.advanced = true;
      requestData.fusion_queries = advancedOptions.fusionQueries;
      requestData.explain_reasoning = advancedOptions.explainReasoning;
      if (advancedOptions.confidenceThreshold > 0) {
        requestData.filters = { confidence_threshold: advancedOptions.confidenceThreshold / 100 };
      }
    }
    onSubmit(requestData);
    setQuery('');   // clear the box after sending (chat behavior)
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const runExample = (ex) => {
    setQuery(ex);
    onSubmit({ query: ex, include_sources: true, max_results: 10 });
  };

  return (
    <div className={`composer ${home ? 'composer-home' : ''}`}>
      <form onSubmit={(e) => { e.preventDefault(); submit(); }}>
        <div className="composer-box">
          <textarea
            ref={taRef}
            className="composer-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a legal question…"
            maxLength={1000}
            rows={1}
            disabled={loading}
          />
          <div className="composer-actions">
            <button
              type="button"
              className={`ghost-btn ${advancedMode ? 'active' : ''}`}
              onClick={() => { setAdvancedMode((v) => !v); setShowAdvanced((v) => !advancedMode ? true : v); }}
              title="Advanced retrieval options"
            >
              <SlidersIcon /> Advanced
            </button>
            <button
              type="submit"
              className="send-btn"
              disabled={loading || !query.trim()}
              aria-label="Send"
            >
              {loading ? <span className="send-spinner" /> : <ArrowUpIcon />}
            </button>
          </div>
        </div>

        {advancedMode && showAdvanced && (
          <div className="advanced-panel">
            <div className="adv-row">
              <label className="adv-label">Query reformulations</label>
              <div className="adv-control">
                <input type="range" min="1" max="10" value={advancedOptions.fusionQueries}
                  onChange={(e) => setAdvancedOptions({ ...advancedOptions, fusionQueries: parseInt(e.target.value) })} />
                <span className="adv-val">{advancedOptions.fusionQueries}</span>
              </div>
            </div>
            <div className="adv-row">
              <label className="adv-label">Min confidence</label>
              <div className="adv-control">
                <input type="range" min="0" max="90" step="10" value={advancedOptions.confidenceThreshold}
                  onChange={(e) => setAdvancedOptions({ ...advancedOptions, confidenceThreshold: parseInt(e.target.value) })} />
                <span className="adv-val">{advancedOptions.confidenceThreshold}%</span>
              </div>
            </div>
            <label className="adv-check">
              <input type="checkbox" checked={advancedOptions.explainReasoning}
                onChange={(e) => setAdvancedOptions({ ...advancedOptions, explainReasoning: e.target.checked })} />
              Show reasoning &amp; reformulations
            </label>
          </div>
        )}
      </form>

      {home && (
        <div className="examples">
          {examples.map((ex, i) => (
            <button key={i} className="example-chip" onClick={() => runExample(ex)} disabled={loading}>
              {ex}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ArrowUpIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" />
    </svg>
  );
}
function SlidersIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" />
      <line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" />
      <line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" />
      <line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" /><line x1="17" y1="16" x2="23" y2="16" />
    </svg>
  );
}

export default QueryForm;
