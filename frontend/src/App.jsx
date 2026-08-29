import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import Topbar from './components/Topbar/Topbar';
import Overview from './pages/Overview/Overview';
import Gateway from './pages/Gateway/Gateway';
import './App.css';

export function App() {
  const [isChatOpen, setIsChatOpen] = useState(true);

  return (
    <div className="app-layout">
      <Topbar
        isChatOpen={isChatOpen}
        onToggleChat={() => setIsChatOpen((prev) => !prev)}
      />
      <div className="app-body">
        <main className="app-content">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/gateway" element={<Gateway />} />
          </Routes>
        </main>

        {/* Chat Dock slot — Person 2 plugs <ChatDock /> here */}
        <aside className={`app-chat-slot ${isChatOpen ? '' : 'collapsed'}`}>
          <div style={{ padding: '16px', color: 'var(--muted)', fontSize: '0.85rem' }}>
            <span className="mono">[ChatDock slot — Person 2]</span>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default App;
