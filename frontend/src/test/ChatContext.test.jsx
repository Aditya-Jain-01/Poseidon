import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { ChatProvider, useChat } from '../context/ChatContext';
import { AgentContext } from '../context/AgentContext';
import * as chatApi from '../api/chat';

function TestConsumer() {
  const {
    sessions,
    activeSessionId,
    messages,
    sendMessage,
    createNewSession,
    switchSession,
    handleApprovalDecision,
    approvalStatuses,
    error,
  } = useChat();

  return (
    <div>
      <div data-testid="active-session-id">{activeSessionId}</div>
      <div data-testid="session-count">{sessions.length}</div>
      <div data-testid="message-count">{messages.length}</div>
      <div data-testid="error-msg">{error || ''}</div>
      {messages.map((m) => (
        <div key={m.id} data-testid="msg-item">
          {m.role}: {m.content} (run: {m.runId || 'none'})
        </div>
      ))}
      {Object.entries(approvalStatuses).map(([id, info]) => (
        <div key={id} data-testid={`approval-status-${id}`}>
          {info.status}: {info.error || 'ok'}
        </div>
      ))}
      <button onClick={() => sendMessage('Hello world')}>Send Message</button>
      <button onClick={() => createNewSession()}>New Session</button>
      <button onClick={() => switchSession(sessions[1]?.id)}>Switch to Second</button>
      <button onClick={() => handleApprovalDecision('app-1', 'approved', sessions[1]?.id)}>
        Approve app-1 for First
      </button>
    </div>
  );
}

describe('ChatContext Provider', () => {
  const mockAgentContext = {
    activeAgentId: 'nereus',
    activeAgent: { id: 'nereus' },
    agents: [{ id: 'nereus' }],
  };

  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  const renderWithContext = (agentOverrides = {}) => {
    return render(
      <AgentContext.Provider value={{ ...mockAgentContext, ...agentOverrides }}>
        <ChatProvider>
          <TestConsumer />
        </ChatProvider>
      </AgentContext.Provider>
    );
  };

  it('sends thread_id and selected agent_id with chat requests', async () => {
    const sendSpy = vi.spyOn(chatApi, 'sendChatMessage').mockResolvedValue({
      reply: 'Nereus response',
      run_id: 'run-123',
      active_agent: 'nereus',
      thread_id: 'session-test',
    });

    renderWithContext({ activeAgentId: 'nereus' });

    const activeSessionId = screen.getByTestId('active-session-id').textContent;
    const sendBtn = screen.getByText('Send Message');

    await act(async () => {
      sendBtn.click();
    });

    expect(sendSpy).toHaveBeenCalledWith(
      'Hello world',
      'local_user',
      expect.anything(),
      activeSessionId,
      'nereus'
    );

    await waitFor(() => {
      expect(screen.getByText(/Nereus response/i)).toBeInTheDocument();
    });
  });

  it('maintains session isolation across multiple conversations', async () => {
    vi.spyOn(chatApi, 'sendChatMessage').mockResolvedValue({
      reply: 'Reply 1',
      run_id: 'run-1',
    });

    renderWithContext();

    // Send in session 1
    await act(async () => {
      screen.getByText('Send Message').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('message-count')).toHaveTextContent('2');
    });

    // Create session 2
    await act(async () => {
      screen.getByText('New Session').click();
    });

    // Session 2 is empty!
    expect(screen.getByTestId('message-count')).toHaveTextContent('0');
    expect(screen.getByTestId('session-count')).toHaveTextContent('2');
  });

  it('binds approval resolution to originating session even when user switched sessions', async () => {
    vi.spyOn(chatApi, 'sendChatMessage').mockResolvedValue({
      reply: 'Needs confirmation',
      run_id: 'run-gate',
      approval_request: { id: 'app-1', tool_name: 'notes_reminders_create' },
    });

    const approveSpy = vi.spyOn(chatApi, 'sendApprovalDecision').mockResolvedValue({
      reply: 'Action approved and executed.',
      run_id: 'run-gate',
      active_agent: 'nereus',
    });

    renderWithContext();

    // Send in session 1
    await act(async () => {
      screen.getByText('Send Message').click();
    });

    // Create session 2 and switch to it
    await act(async () => {
      screen.getByText('New Session').click();
    });
    expect(screen.getByTestId('message-count')).toHaveTextContent('0');

    // While on session 2, approve app-1 for session 1
    await act(async () => {
      screen.getByText('Approve app-1 for First').click();
    });

    expect(approveSpy).toHaveBeenCalledWith('app-1', 'approved');

    // Current session 2 remains clean (does NOT have the resumed response!)
    expect(screen.getByTestId('message-count')).toHaveTextContent('0');

    // Switch back to session 1
    await act(async () => {
      screen.getByText('Switch to Second').click();
    });

    // Session 1 now has the resumed message!
    await waitFor(() => {
      expect(screen.getByText(/Action approved and executed/i)).toBeInTheDocument();
    });
  });

  it('tracks failure in approvalStatuses when submission fails', async () => {
    vi.spyOn(chatApi, 'sendApprovalDecision').mockRejectedValueOnce(
      new Error('Approval rejected by security policy')
    );

    renderWithContext();

    await act(async () => {
      screen.getByText('Approve app-1 for First').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('approval-status-app-1')).toHaveTextContent(
        'failed: Approval rejected by security policy'
      );
    });
  });
});
