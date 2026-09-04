import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Brain, Calendar, FileText, ExternalLink } from 'lucide-react';
import './MemoryAccordion.css';

export function MemoryAccordion({ memoryContext, onInspectTurn }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!memoryContext) return null;

  const { semantic_facts = [], episodic_events = [], procedural_skills = [] } = memoryContext;
  const totalCount = semantic_facts.length + episodic_events.length + procedural_skills.length;

  if (totalCount === 0) return null;

  const summaryParts = [];
  if (semantic_facts.length > 0) {
    summaryParts.push(`${semantic_facts.length} ${semantic_facts.length === 1 ? 'fact' : 'facts'}`);
  }
  if (episodic_events.length > 0) {
    summaryParts.push(`${episodic_events.length} past ${episodic_events.length === 1 ? 'event' : 'events'}`);
  }
  if (procedural_skills.length > 0) {
    summaryParts.push(`${procedural_skills.length} ${procedural_skills.length === 1 ? 'skill' : 'skills'}`);
  }

  return (
    <div className={`memory-accordion-root ${isOpen ? 'is-open' : ''}`}>
      <button
        type="button"
        className="memory-accordion-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <div className="memory-accordion-toggle-left">
          <Brain size={14} className="memory-brain-icon" />
          <span className="memory-accordion-label">Recalled {summaryParts.join(' · ')}</span>
        </div>
        <div className="memory-accordion-toggle-right">
          <span className="memory-view-text">{isOpen ? 'Hide context' : 'Show context'}</span>
          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {isOpen && (
        <div className="memory-accordion-content animate-fade-in">
          {semantic_facts.length > 0 && (
            <div className="memory-section">
              <div className="memory-section-title">
                <Brain size={12} />
                <span>Semantic Facts (MEMORY.md)</span>
              </div>
              <ul className="memory-fact-list">
                {semantic_facts.map((fact, idx) => (
                  <li key={idx} className="memory-fact-item">
                    {fact}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {episodic_events.length > 0 && (
            <div className="memory-section">
              <div className="memory-section-title">
                <Calendar size={12} />
                <span>Episodic Events Recalled</span>
              </div>
              <div className="memory-episodic-list">
                {episodic_events.map((ev, idx) => (
                  <div key={idx} className="memory-episodic-item">
                    <span className="episodic-role">{ev.role || 'turn'}:</span>
                    <span className="episodic-content">{ev.content}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {procedural_skills.length > 0 && (
            <div className="memory-section">
              <div className="memory-section-title">
                <FileText size={12} />
                <span>Procedural Playbooks (*.SKILL.md)</span>
              </div>
              <div className="memory-skills-list">
                {procedural_skills.map((skill, idx) => (
                  <span key={idx} className="memory-skill-badge">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {onInspectTurn && (
            <div className="memory-accordion-footer">
              <button
                type="button"
                className="memory-inspect-link"
                onClick={onInspectTurn}
              >
                <span>Open Deep Inspector in Side Panel</span>
                <ExternalLink size={12} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MemoryAccordion;
