import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Gateway from '../pages/Gateway/Gateway';
import { ChatContext } from '../context/ChatContext';
import { HealthContext } from '../context/HealthContext';
import * as auditApi from '../api/audit';

describe('Gateway Component', () => {
  const mockChatContext = {
    sessions: [{ id: 's1', title: 'Session 1', messages: [] }],
    activeSessionId: 's1',
    switchSession: vi.fn(),
    inspectTurn: vi.fn(),
  };

  const mockHealthContext = {
    isConnected: true,
    telegramPolling: true,
  };

  const sampleEvents = [
    {
      event_id: 'evt_1234567890abcdef',
      run_id: 'run_web_001',
      owner_id: 'local_owner',
      channel: 'web',
      direction: 'inbound',
      event_type: 'chat_request',
      status: 'completed',
      payload: { text: 'Hello Poseidon' },
      created_at: new Date().toISOString(),
    },
    {
      event_id: 'evt_abcdef1234567890',
      run_id: 'telegram_update_99',
      owner_id: 'local_owner',
      channel: 'telegram',
      direction: 'inbound',
      event_type: 'telegram_message',
      status: 'completed',
      payload: { text: 'Check tasks' },
      created_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(auditApi, 'fetchGatewayEvents').mockResolvedValue({
      count: 2,
      events: sampleEvents,
    });
  });

  const renderGateway = (healthOverrides = {}) => {
    return render(
      <MemoryRouter>
        <HealthContext.Provider value={{ ...mockHealthContext, ...healthOverrides }}>
          <ChatContext.Provider value={mockChatContext}>
            <Gateway />
          </ChatContext.Provider>
        </HealthContext.Provider>
      </MemoryRouter>
    );
  };

  it('renders durable backend events in the ledger', async () => {
    renderGateway();

    await waitFor(() => {
      expect(screen.getByText('chat_request')).toBeInTheDocument();
      expect(screen.getByText('telegram_message')).toBeInTheDocument();
    });

    expect(screen.getByText('run_web_00...')).toBeInTheDocument();
    expect(screen.getByText('telegram_u...')).toBeInTheDocument();
    expect(screen.getAllByText('IN')).toHaveLength(2);
  });

  it('shows Telegram tab when telegram is configured', async () => {
    renderGateway({ telegramPolling: true });

    await waitFor(() => {
      expect(screen.getByText('Telegram')).toBeInTheDocument();
      expect(screen.getByText('Polling Active')).toBeInTheDocument();
    });
  });

  it('hides Telegram tab when telegram is not configured', async () => {
    renderGateway({ telegramPolling: false });

    await waitFor(() => {
      expect(screen.queryByText('Telegram')).not.toBeInTheDocument();
    });
  });

  it('keeps Discord completely absent from the gateway page', async () => {
    renderGateway();

    await waitFor(() => {
      expect(screen.queryByText(/Discord/i)).not.toBeInTheDocument();
    });
  });
});
