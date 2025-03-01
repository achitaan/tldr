import './App.css';
import React, { useState } from 'react';
import OpenCvComponent from './components/RunOpenCV';
import ChatButton from './components/ChatButton';
import ChatBar from './components/ChatBar';

const App = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);

  const handleToggleChat = () => {
    setIsChatOpen((prev) => !prev);
  };

  return (
    <div style={{ margin: '40px' }}>
      <h1>TLDR</h1>
      {/* Button that toggles the chat bar */}
      <ChatButton onClick={handleToggleChat} isOpen={isChatOpen} />
      {/* The chat bar component */}
      <ChatBar isOpen={isChatOpen} />
      <OpenCvComponent />
    </div>
  );
};

export default App;