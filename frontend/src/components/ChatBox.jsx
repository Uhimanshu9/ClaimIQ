import React, { useState } from "react";

const MessageBubble = ({ msg }) => {
  const [showThinking, setShowThinking] = useState(false);

  return (
    <div className={`message-wrapper ${msg.role}`}>
      <div className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}>
        {msg.role === "assistant" && (
          <div className="assistant-avatar">
            {msg.isError ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            )}
          </div>
        )}
        
        <div className="message-content">
          <p className="message-text">{msg.content}</p>
          
          {msg.role === "assistant" && msg.thinking && (
            <div className="thinking-section">
              <button
                className="thinking-toggle"
                onClick={() => setShowThinking(!showThinking)}
                aria-expanded={showThinking}
              >
                <span>{showThinking ? "Hide Thinking" : "Show Thinking"}</span>
                <svg 
                  className={`chevron ${showThinking ? "expanded" : ""}`}
                  width="16" 
                  height="16" 
                  viewBox="0 0 24 24" 
                  fill="currentColor"
                >
                  <path d="M7.41 8.84L12 13.42l4.59-4.58L18 10.25l-6 6-6-6z"/>
                </svg>
              </button>
              
              <div className={`thinking-content ${showThinking ? "expanded" : ""}`}>
                <div className="thinking-header">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9 11H7v8h2v-8zm4 0h-2v8h2v-8zm4 0h-2v8h2v-8zm2.5-9H20v2H4V2h3.5l1-1h7l1 1z"/>
                  </svg>
                  <span>{msg.isError ? "Error Details" : "Detailed Analysis"}</span>
                </div>
                <div className="thinking-text">{msg.thinking}</div>
              </div>
            </div>
          )}
        </div>

        {msg.role === "user" && (
          <div className="user-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;