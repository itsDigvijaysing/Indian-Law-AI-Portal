import React from 'react';
import './Header.css';

function Header({ llmStatus }) {
  return (
    <header className="header">
      <h1>Indian Law AI Portal</h1>
      <p>AI-powered legal query assistant for Indian laws</p>
      {llmStatus && llmStatus !== 'active' && (
        <span className="header-badge">Limited Mode - No API Key</span>
      )}
    </header>
  );
}

export default Header;
