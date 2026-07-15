import React, { useEffect } from 'react';
import { GITHUB_URL } from '../config';
import './RateLimitModal.css';

// Turn an ISO reset timestamp into a friendly "resets in 7h 20m".
function formatReset(resetAt) {
  if (!resetAt) return null;
  const ms = new Date(resetAt).getTime() - Date.now();
  if (!Number.isFinite(ms) || ms <= 0) return 'shortly';
  const mins = Math.round(ms / 60000);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h <= 0) return `in ${m} min`;
  if (m === 0) return `in ${h} h`;
  return `in ${h} h ${m} min`;
}

function RateLimitModal({ info, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const limit = info?.limit ?? 25;
  const resetIn = formatReset(info?.reset_at);

  return (
    <div className="rl-backdrop" onClick={onClose} role="presentation">
      <div
        className="rl-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rl-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="rl-close" onClick={onClose} aria-label="Close">
          <CloseIcon />
        </button>

        <div className="rl-badge" aria-hidden="true"><GaugeIcon /></div>

        <h2 className="rl-title" id="rl-title">You've reached today's free limit</h2>

        <p className="rl-lead">
          This portal is a <strong>free, open-source</strong> project running on a personal
          budget with no paid backing. To keep it online for everyone, it's capped at{' '}
          <strong>{limit} question{limit === 1 ? '' : 's'} per day</strong>.
        </p>

        <div className="rl-reset">
          <ClockIcon />
          <span>The free quota resets {resetIn ? <strong>{resetIn}</strong> : 'at midnight UTC'}.</span>
        </div>

        <div className="rl-pitch">
          <p className="rl-pitch-title">Want unlimited answers now?</p>
          <p className="rl-pitch-body">
            Because it's open source, you can run your own copy with a free Groq API key,
            no daily limit. Everything you need is on GitHub.
          </p>
        </div>

        <div className="rl-actions">
          <a className="rl-btn rl-btn-primary" href={GITHUB_URL} target="_blank" rel="noreferrer">
            <GithubIcon /> View on GitHub
          </a>
          <button className="rl-btn rl-btn-ghost" onClick={onClose}>Maybe later</button>
        </div>

        <p className="rl-foot">Thanks for understanding, and for supporting a free project.</p>
      </div>
    </div>
  );
}

function GaugeIcon() {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 13a4 4 0 0 1 4-4" />
      <path d="M4 20a8 8 0 1 1 16 0" />
      <line x1="12" y1="13" x2="15.5" y2="9.5" />
    </svg>
  );
}
function ClockIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15.5 14" />
    </svg>
  );
}
function GithubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .4.2.7.8.6 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5z" />
    </svg>
  );
}
function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
  );
}

export default RateLimitModal;
