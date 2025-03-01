import React from 'react';
import './ChatBar.css';

const ChatButton = ({ onClick, isOpen }) => {
  // We add the "open" class if isOpen is true
  const buttonClass = `chat-toggle-btn ${isOpen ? 'open' : ''}`;

  return (
    <button className={buttonClass} onClick={onClick}>
      {isOpen ? 'Close Chat' : 'Open Chat'}
    </button>
  );
};

export default ChatButton;