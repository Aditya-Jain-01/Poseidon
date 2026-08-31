import React from 'react';
import { 
  Sun, 
  Moon, 
  PanelRight
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import './Topbar.css';

export function Topbar({ isRightPanelOpen, onToggleRightPanel }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="topbar">
      {/* Right Utilities */}
      <div className="topbar-right">
        {/* Theme Toggle Button */}
        <button
          className="topbar-icon-btn theme-toggle-btn"
          onClick={toggleTheme}
          title={theme === 'dark' ? "Switch to Light Theme" : "Switch to Dark Theme"}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* Inspector Toggle */}
        <button
          className={`topbar-icon-btn ${isRightPanelOpen ? 'active' : ''}`}
          onClick={onToggleRightPanel}
          title="Toggle Trajectory &amp; Telemetry Inspector"
          aria-label="Toggle Inspector"
        >
          <PanelRight size={16} />
        </button>
      </div>
    </header>
  );
}

export default Topbar;
