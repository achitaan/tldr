import React, { useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import './App.css';

// routing
import router from './routes';
import NavigationScroll from './layout/NavigationScroll';

// theme
import ThemeCustomization from './themes';

// custom components
import OpenCvComponent from './components/RunOpenCV';
import ChatButton from './components/ChatButton';
import ChatBar from './components/ChatBar';

const App = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);

  const handleToggleChat = () => {
    setIsChatOpen((prev) => !prev);
  };

  return (
    <ThemeCustomization>
      <NavigationScroll>
        <div className="app-container">
          {/* Camera Section */}
          <div className="camera-section">
            <OpenCvComponent />
          </div>
          
          {/* Content Section */}
          <div className="content-section">
            <h1>TLDR</h1>
            <RouterProvider router={router} />
          </div>

          {/* Chat Controls */}
          <div className="chat-controls">
            <ChatButton onClick={handleToggleChat} isOpen={isChatOpen} />
            <ChatBar isOpen={isChatOpen} />
          </div>
        </div>
      </NavigationScroll>
    </ThemeCustomization>
  );
};

export default App;
