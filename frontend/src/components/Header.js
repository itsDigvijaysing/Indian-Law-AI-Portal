import React from 'react';
import { GITHUB_URL } from '../config';
import './Header.css';

function Header({ llmStatus, status, onMenu, theme, onToggleTheme, onNew, hasThread }) {
  const healthy = status?.status === 'healthy';
  const dotClass = !status ? 'idle' : healthy ? 'ok' : 'warn';
  const statusText = !status
    ? 'Connecting…'
    : healthy
      ? `${status.total_documents?.toLocaleString?.() || status.total_documents} passages · ${status.available_agents} agents`
      : 'Starting up…';

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button className="menu-btn" onClick={onMenu} aria-label="Toggle sidebar">
          <span /><span /><span />
        </button>

        <button className="brand" onClick={onNew} title="New conversation">
          <FlagMark />
          <span className="brand-name">Indian Law<span className="brand-dim"> AI</span></span>
        </button>

        <div className="topbar-right">
          <div className="topbar-status" title={statusText}>
            <span className={`status-dot ${dotClass}`} />
            <span className="status-text">{statusText}</span>
            {llmStatus && llmStatus !== 'active' && <span className="limited-pill">Limited</span>}
          </div>

          {hasThread && (
            <button className="icon-btn new-btn" onClick={onNew} title="New conversation">
              <PlusIcon /> <span className="new-label">New</span>
            </button>
          )}

          <a className="icon-btn github-btn" href={GITHUB_URL} target="_blank" rel="noreferrer"
             title="Free & open source — view on GitHub" aria-label="View source on GitHub">
            <GithubIcon /> <span className="github-label">Open source</span>
          </a>

          <button className="icon-btn" onClick={onToggleTheme} aria-label="Toggle theme"
                  title={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}>
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </div>
    </header>
  );
}

function FlagMark() {
  const spokes = Array.from({ length: 12 }, (_, i) => {
    const a = (i * 30 * Math.PI) / 180;
    return <line key={i} x1="15" y1="15" x2={15 + 3.1 * Math.cos(a)} y2={15 + 3.1 * Math.sin(a)} />;
  });
  return (
    <svg className="brand-flag" width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
      <defs><clipPath id="flagRound"><rect x="0" y="0" width="30" height="30" rx="8" /></clipPath></defs>
      <g clipPath="url(#flagRound)">
        <rect x="0" y="0" width="30" height="10" fill="var(--flag-saffron)" />
        <rect x="0" y="10" width="30" height="10" fill="#ffffff" />
        <rect x="0" y="20" width="30" height="10" fill="var(--flag-green)" />
        <g stroke="var(--flag-navy)" strokeWidth="0.7" fill="none">
          <circle cx="15" cy="15" r="3.1" />
          {spokes}
        </g>
        <circle cx="15" cy="15" r="0.9" fill="var(--flag-navy)" />
      </g>
      <rect x="0.5" y="0.5" width="29" height="29" rx="7.5" fill="none" stroke="rgba(0,0,0,0.10)" />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .4.2.7.8.6 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5z" />
    </svg>
  );
}
function MoonIcon() {
  return (<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>);
}
function SunIcon() {
  return (<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4.2" /><line x1="12" y1="1.5" x2="12" y2="4" /><line x1="12" y1="20" x2="12" y2="22.5" /><line x1="3.5" y1="3.5" x2="5.3" y2="5.3" /><line x1="18.7" y1="18.7" x2="20.5" y2="20.5" /><line x1="1.5" y1="12" x2="4" y2="12" /><line x1="20" y1="12" x2="22.5" y2="12" /><line x1="3.5" y1="20.5" x2="5.3" y2="18.7" /><line x1="18.7" y1="5.3" x2="20.5" y2="3.5" /></svg>);
}
function PlusIcon() {
  return (<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>);
}

export default Header;
