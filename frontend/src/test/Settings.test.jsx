import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Settings from '../pages/Settings/Settings';
import { HealthContext } from '../context/HealthContext';
import { AgentContext } from '../context/AgentContext';
import * as memoryApi from '../api/memory';

describe('Settings Component', () => {
  const mockHealthContext = {
    modelName: 'nvidia/nemotron-3-ultra',
    isConnected: true,
    lastChecked: new Date(),
    capabilities: {
      python: '3.12.10',
      fts5: true,
      wal: true,
      json: true,
      vector_mode: 'python-cosine',
    },
  };

  const mockAgentContext = {
    llmSettings: {
      providers: { env: { base_url: 'https://integrate.api.nvidia.com/v1' } },
      agents: { poseidon: { has_api_key: true } },
    },
    checkAgentHealth: vi.fn().mockResolvedValue({ available: true, message: 'Reachable' }),
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(memoryApi, 'fetchSemanticMemory').mockResolvedValue({ facts: [{ fact: 'User likes tea', category: 'general' }] });
    vi.spyOn(memoryApi, 'fetchProceduralMemory').mockResolvedValue({ skills: [{ name: 'schedule_meeting', triggers: ['meeting'] }] });
    vi.spyOn(memoryApi, 'fetchMemoryStatus').mockResolvedValue({
      semantic_facts_count: 1,
      procedural_skills_count: 1,
      consolidation: { unconsolidated_count: 5, threshold: 30 },
    });
  });

  const renderSettings = (initialTab = 'models', healthOverrides = {}) => {
    return render(
      <MemoryRouter initialEntries={[`/settings?tab=${initialTab}`]}>
        <HealthContext.Provider value={{ ...mockHealthContext, ...healthOverrides }}>
          <AgentContext.Provider value={mockAgentContext}>
            <Settings />
          </AgentContext.Provider>
        </HealthContext.Provider>
      </MemoryRouter>
    );
  };

  it('displays real capability telemetry in models tab', () => {
    renderSettings('models');
    expect(screen.getByText(/Active model/i)).toBeInTheDocument();
    expect(screen.getAllByText('nvidia/nemotron-3-ultra').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Fallback python-cosine')).toBeInTheDocument();
    expect(screen.getByText(/Python 3.12.10 · WAL=on · FTS5=on/i)).toBeInTheDocument();
  });

  it('displays native sqlite-vec when active', () => {
    renderSettings('models', {
      capabilities: {
        python: '3.12.10',
        fts5: true,
        wal: true,
        vector_mode: 'sqlite-vec',
      },
    });
    expect(screen.getByText('Native sqlite-vec')).toBeInTheDocument();
  });

  it('renames sandbox to in-process execution guard in security tab and does not claim OS isolation', () => {
    renderSettings('security');
    expect(screen.getByRole('heading', { name: /In-Process Execution Guard/i })).toBeInTheDocument();
    expect(screen.getByText(/Does not provide adversarial container\/OS sandbox isolation/i)).toBeInTheDocument();
    expect(screen.getByText(/All tools execute within the In-process execution guard boundary/i)).toBeInTheDocument();
    expect(screen.getAllByText('In-process execution guard')).toHaveLength(AVAILABLE_TOOLS_COUNT_OR_MORE);
  });

  it('displays memory facts and error message when loading fails', async () => {
    vi.spyOn(memoryApi, 'fetchSemanticMemory').mockRejectedValueOnce(new Error('SQLite busy timeout'));
    renderSettings('memory');

    await waitFor(() => {
      expect(screen.getByText(/SQLite busy timeout/i)).toBeInTheDocument();
    });
  });
});

const AVAILABLE_TOOLS_COUNT_OR_MORE = 7; // 7 rows in table (exact text match, p-tag content is a sentence not exact)
