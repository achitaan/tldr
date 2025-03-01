import React from 'react';
import './ChatBar.css';

const ChatBar = ({ isOpen }) => {
  // We add the "open" class if isOpen is true
  const containerClass = `chat-bar-container ${isOpen ? 'open' : ''}`;

  return (
    <div className={containerClass}>
      {isOpen && (
        <div className="chat-content">
          <p>Welcome to the chat!</p>
          <p>Type your message here...</p>
          {/* Add your input/message list here */}
        </div>
      )}
    </div>
  );
};

export default ChatBar;