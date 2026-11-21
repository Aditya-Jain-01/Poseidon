import React, { useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { PanelLeft, PanelRight } from 'lucide-react';
import SettingsDialog from './pages/Settings/SettingsDialog';
import LeftSidebar from './components/LeftSidebar/LeftSidebar';
import RightPanel from './components/RightPanel/RightPanel';
import AgentView from './components/AgentView/AgentView';
import Gateway from './pages/Gateway/Gateway';
import Brain from './pages/Brain/Brain';
import { ChatProvider, useChat } from './context/ChatContext';
import { HealthProvider } from './context/HealthContext';
import { ThemeProvider } from './context/ThemeContext';
import { AgentProvider } from './context/AgentContext';
import ChatDock from './components/ChatDock/ChatDock';
import { useWorkspaceLayout } from './layout/useWorkspaceLayout';
import './App.css';
import './ReferenceShell.css';

function AppLayout() {
  const location = useLocation();
  const [sidebarMode, setSidebarMode] = useState('chat'); // 'chat' | 'agents'

  const { isOverviewOpen, toggleOverview } = useChat();
  const detailsOpen = isOverviewOpen && sidebarMode !== 'agents';
  const { columns, sidebarCollapsed, toggleSidebar, dragging, sidebarResize, detailsResize } = useWorkspaceLayout(detailsOpen);
  const handleToggleRight = () => toggleOverview();

  return (
    <div
      className="app-workspace-layout"
      data-dragging={dragging}
      data-details-overlay={columns.detailsOverlay}
      style={{ '--workspace-rail': `${columns.rail}px`, '--workspace-sidebar': `${columns.gridSidebar}px`, '--workspace-details': `${columns.gridDetails}px` }}
    >
      {/* 1. Left Navigation Sidebar */}
      <LeftSidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebar}
        width={columns.sidebar}
        resizeHandlers={sidebarResize}
        sidebarMode={sidebarMode}
        onModeChange={setSidebarMode}
      />

      {/* 2. Center Main Canvas */}
      <div className="center-workspace">
        <header className="workspace-topbar">
          <button type="button" className="workspace-mobile-toggle" onClick={toggleSidebar} aria-label="Toggle sidebar"><PanelLeft size={19} /></button>
          <button type="button" className="workspace-topbar-inspector" onClick={handleToggleRight} aria-label="Toggle inspector" title="Toggle inspector"><PanelRight size={18} /></button>
        </header>
        <main className="center-content">
          <Routes>
            <Route path="/" element={sidebarMode === 'agents' ? <AgentView /> : <ChatDock />} />
            <Route path="/gateway" element={<Gateway />} />
            <Route path="/settings" element={<ChatDock />} />
            <Route path="/brain" element={<Brain />} />
          </Routes>
        </main>
      </div>

      {location.pathname === '/settings' && <SettingsDialog />}
      {/* 3. Right Inspector Panel */}
      <RightPanel
        isCollapsed={!detailsOpen}
        onToggleCollapse={handleToggleRight}
        width={columns.details}
        resizeHandlers={detailsResize}
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
