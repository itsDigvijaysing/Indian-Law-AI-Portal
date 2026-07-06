import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import Header from './components/Header';
import QueryForm from './components/QueryForm';
import ResponseDisplay from './components/ResponseDisplay';
import QueryHistory from './components/QueryHistory';
import DocumentManager from './components/DocumentManager';
import Footer from './components/Footer';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';
const MAX_HISTORY = 20;

// Backend errors carry string `detail`, but 422 validation errors carry an
// ARRAY of objects — rendering that in JSX crashes React. Always normalize.
function errorToString(err, fallback) {
  const detail = err.response?.data?.detail ?? err.response?.data?.error;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
  }
  return err.message || fallback;
}

let turnSeq = 0;

function App() {
  const [turns, setTurns] = useState([]);       // conversation thread
  const [loading, setLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
  const bottomRef = React.useRef(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);
  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  const loadSystemStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/health`);
      setSystemStatus(res.data);
    } catch (err) {
      console.error('Failed to load system status:', err);
    }
  }, []);

  useEffect(() => {
    loadSystemStatus();
  }, [loadSystemStatus]);

  // While the backend is still initializing (model downloads/ingestion), the
  // first health fetch reports "initializing"/"unknown" — poll until healthy
  // so the header badge doesn't stay stuck on a stale state.
  useEffect(() => {
    if (systemStatus?.status === 'healthy') return undefined;
    const timer = setInterval(loadSystemStatus, 10000);
    return () => clearInterval(timer);
  }, [systemStatus, loadSystemStatus]);

  // Patch the fields of one turn (by id) as its answer streams in.
  const patchTurn = (id, patch) =>
    setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));

  // Stream the answer over SSE into a specific turn.
  const streamQuery = async (requestData, id) => {
    const res = await fetch(`${API_BASE_URL}/api/v1/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData),
    });
    if (!res.ok || !res.body) throw new Error(`Stream failed (${res.status})`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let event = null;
    let answer = '';
    let base = {};
    let final = null;

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          event = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          if (event === 'sources') {
            base = data;
            patchTurn(id, { data: { ...base, answer, streaming: true } });
          } else if (event === 'token') {
            answer += data.text || '';
            patchTurn(id, { data: { ...base, answer, streaming: true } });
          } else if (event === 'done') {
            final = data;
            patchTurn(id, { data, streaming: false });
          } else if (event === 'error') {
            throw new Error(data.error || 'Stream error');
          }
        }
      }
    }
    if (!final) throw new Error('Stream ended without completion');
    return final;
  };

  const handleQuery = async (requestData) => {
    const id = ++turnSeq;
    setLoading(true);
    setTurns((prev) => [...prev, { id, query: requestData.query, data: null, streaming: true, error: null }]);
    // Record in Recent with this turn's id so clicking it later scrolls here.
    setHistory((prev) => {
      const entry = { query: requestData.query, turnId: id, requestData };
      const next = [entry, ...prev.filter((h) => h.query !== requestData.query)];
      return next.slice(0, MAX_HISTORY);
    });
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 30);

    try {
      let data;
      if (requestData.advanced) {
        const result = await axios.post(`${API_BASE_URL}/api/v1/query/advanced`, requestData);
        data = result.data;
        patchTurn(id, { data, streaming: false });
      } else {
        try {
          data = await streamQuery(requestData, id);
        } catch (streamErr) {
          console.warn('Streaming failed, using standard endpoint:', streamErr);
          patchTurn(id, { data: null, streaming: true });
          const result = await axios.post(`${API_BASE_URL}/api/v1/query`, requestData);
          data = result.data;
          patchTurn(id, { data, streaming: false });
        }
      }

      // Tag the recent entry with the answering agent (for the sublabel).
      setHistory((prev) => prev.map((h) => (h.turnId === id ? { ...h, agent: data.agent_type } : h)));
    } catch (err) {
      patchTurn(id, { streaming: false, error: errorToString(err, 'An error occurred while processing your query') });
    } finally {
      setLoading(false);
    }
  };

  // Clicking Recent: if that turn is still in the current thread, scroll to it;
  // otherwise (e.g. after "New chat") ask it again.
  const handleHistorySelect = (item) => {
    setSidebarOpen(false);
    const exists = turns.some((t) => t.id === item.turnId);
    if (exists) {
      const el = document.getElementById(`turn-${item.turnId}`);
      if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
    }
    handleQuery(item.requestData);
  };
  const newChat = () => { setTurns([]); setSidebarOpen(false); };

  const llmStatus = systemStatus?.llm_status;
  const isHome = turns.length === 0;

  return (
    <div className="app">
      <Header llmStatus={llmStatus} status={systemStatus} onMenu={() => setSidebarOpen((v) => !v)}
              theme={theme} onToggleTheme={toggleTheme} onNew={newChat} hasThread={!isHome} />

      <div className={`app-body ${isHome ? 'home' : ''}`}>
        {sidebarOpen && <div className="scrim" onClick={() => setSidebarOpen(false)} />}
        <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <QueryHistory history={history} onSelect={handleHistorySelect} loading={loading} />
          <DocumentManager />
        </aside>

        <main className={`main-content ${isHome ? 'is-home' : ''}`}>
          {isHome ? (
            <>
              <div className="hero">
                <h1 className="hero-title">Ask about Indian law</h1>
                <p className="hero-sub">
                  Plain-language answers, with citations to the exact law, section, and page.
                  Grounded in 25 official statutes. No internet sources.
                </p>
              </div>
              <QueryForm onSubmit={handleQuery} loading={loading} home />
              <Footer />
            </>
          ) : (
            <>
              <div className="thread">
                {turns.map((t) => (
                  <div className="turn" id={`turn-${t.id}`} key={t.id}>
                    <div className="turn-q">
                      <span className="turn-q-icon" aria-hidden="true">?</span>
                      <span>{t.query}</span>
                    </div>
                    {t.error ? (
                      <div className="error-state" role="alert">
                        <span className="error-mark">!</span><span>{t.error}</span>
                      </div>
                    ) : t.data ? (
                      <ResponseDisplay response={t.data} />
                    ) : (
                      <div className="thinking" role="status" aria-live="polite">
                        <span className="dots"><span /><span /><span /></span>
                        Searching the statutes…
                      </div>
                    )}
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>

              <div className="composer-dock">
                <QueryForm onSubmit={handleQuery} loading={loading} />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
