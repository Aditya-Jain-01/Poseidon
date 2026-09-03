import React, { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import LeftSidebar from './components/LeftSidebar/LeftSidebar';
import RightPanel from './components/RightPanel/RightPanel';
import Gateway from './pages/Gateway/Gateway';
import Settings from './pages/Settings/Settings';
import { ChatProvider, useChat } from './context/ChatContext';
import { HealthProvider } from './context/HealthContext';
import { ThemeProvider } from './context/ThemeContext';
import { AgentProvider } from './context/AgentContext';
import ChatDock from './components/ChatDock/ChatDock';
import './App.css';

function AppLayout() {
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [isRightCollapsed, setIsRightCollapsed] = useState(true);
  const [rightPanelWidth, setRightPanelWidth] = useState(380);
  const [isResizingRight, setIsResizingRight] = useState(false);

  const { isOverviewOpen, toggleOverview, closeOverview } = useChat();

  // Synchronize context overview toggle with right panel collapse
  useEffect(() => {
    setIsRightCollapsed(!isOverviewOpen);
  }, [isOverviewOpen]);

  // Handle Drag-to-Resize Right Panel
  useEffect(() => {
    if (!isResizingRight) return;

    const handleMouseMove = (e) => {
      const newWidth = window.innerWidth - e.clientX;
      const minWidth = 280;
      const maxWidth = Math.min(850, window.innerWidth * 0.65);
      setRightPanelWidth(Math.max(minWidth, Math.min(newWidth, maxWidth)));
    };

    const handleMouseUp = () => {
      setIsResizingRight(false);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingRight]);

  const handleMouseDownResize = (e) => {
    e.preventDefault();
    setIsResizingRight(true);
  };

  const handleToggleLeft = () => setIsLeftCollapsed((prev) => !prev);
  const handleToggleRight = () => toggleOverview();

  return (
    <div className="app-workspace-layout">
      {/* 1. Left Navigation Sidebar */}
      <LeftSidebar
        isCollapsed={isLeftCollapsed}
        onToggleCollapse={handleToggleLeft}
      />

      {/* 2. Center Main Canvas (Top bar removed) */}
      <div className="center-workspace">
        <main className="center-content">
          <Routes>
            <Route path="/" element={<ChatDock />} />
            <Route path="/gateway" element={<Gateway />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>

      {/* 3. Right Trajectory & Diagnostics Inspector Side Window */}
      <RightPanel
        isCollapsed={isRightCollapsed}
        onToggleCollapse={handleToggleRight}
        width={rightPanelWidth}
        onMouseDownResize={handleMouseDownResize}
      />
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <HealthProvider>
        <AgentProvider>
          <ChatProvider>
            <AppLayout />
          </ChatProvider>
        </AgentProvider>
      </HealthProvider>
    </ThemeProvider>
  );
}

export default App;
