import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Topbar from './components/Topbar/Topbar';
import Overview from './pages/Overview/Overview';
import Gateway from './pages/Gateway/Gateway';
import { ChatProvider, useChat } from './context/ChatContext';
import { HealthProvider } from './context/HealthContext';
import ChatDock from './components/ChatDock/ChatDock';
import './App.css';

function AppLayout() {
  const { isDockOpen, toggleDock, dockWidth, isExpanded } = useChat();

  const currentWidth = isExpanded ? 'min(860px, 65vw)' : `${dockWidth}px`;

  return (
    <div className="app-layout">
      <Topbar
        isChatOpen={isDockOpen}
        onToggleChat={toggleDock}
      />
      <div className="app-body">
        <main className="app-content">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/gateway" element={<Gateway />} />
          </Routes>
        </main>

        <aside
          className={`app-chat-slot ${isDockOpen ? '' : 'collapsed'} ${isExpanded ? 'is-expanded' : ''}`}
          style={{ width: currentWidth, minWidth: isExpanded ? '480px' : '340px' }}
        >
          <ChatDock />
        </aside>
      </div>
    </div>
  );
}

export function App() {
  return (
    <HealthProvider>
      <ChatProvider>
        <AppLayout />
      </ChatProvider>
    </HealthProvider>
  );
}

export default App;
