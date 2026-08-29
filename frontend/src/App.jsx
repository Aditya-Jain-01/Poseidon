import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Topbar from './components/Topbar/Topbar';
import Overview from './pages/Overview/Overview';
import Gateway from './pages/Gateway/Gateway';
import { ChatProvider, useChat } from './context/ChatContext';
import ChatDock from './components/ChatDock/ChatDock';
import './App.css';

function AppLayout() {
  const { isDockOpen, toggleDock } = useChat();

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

        <aside className={`app-chat-slot ${isDockOpen ? '' : 'collapsed'}`}>
          <ChatDock />
        </aside>
      </div>
    </div>
  );
}

export function App() {
  return (
    <ChatProvider>
      <AppLayout />
    </ChatProvider>
  );
}

export default App;
