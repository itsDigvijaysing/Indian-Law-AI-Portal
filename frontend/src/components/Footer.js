import React from 'react';
import { GITHUB_URL } from '../config';
import './Footer.css';

function Footer({ usage }) {
  const showQuota = usage?.enabled;

  return (
    <footer className="footer">
      <div className="footer-badges">
        <span className="footer-badge free">Free &amp; open source</span>
        <span className="footer-badge">No login</span>
        <span className="footer-badge">No ads</span>
        <a className="footer-badge github" href={GITHUB_URL} target="_blank" rel="noreferrer">
          <GithubIcon /> Star on GitHub
        </a>
      </div>

      {showQuota && (
        <p className="footer-quota">
          <span className="quota-dot" aria-hidden="true" />
          {usage.remaining > 0
            ? <><strong>{usage.remaining}</strong> of {usage.limit} free questions left today</>
            : <>Today's free quota is used up. It resets at midnight UTC.</>}
        </p>
      )}

      <p className="footer-note">
        A free, unpaid community project. Grounded in official Indian statutes. Not legal advice.
        Please consult a qualified professional.
      </p>
      <p className="footer-sources">
        Authorized source corpus:{' '}
        <a href="https://www.indiacode.nic.in/" target="_blank" rel="noreferrer">
          indiacode.nic.in
        </a>{' '}
        and{' '}
        <a href="https://www.legislative.gov.in/" target="_blank" rel="noreferrer">
          legislative.gov.in
        </a>
      </p>
    </footer>
  );
}

function GithubIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .4.2.7.8.6 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5z" />
    </svg>
  );
}

export default Footer;
