import React, { createContext, useContext, useCallback, useRef, useState, useEffect } from 'react';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { sendChatMessage, sendApprovalDecision } from '../api/chat';

export const ChatContext = createContext(null);

/**
 * Creates a default initial session object.
 */
function createNewSessionObject(title = 'New Conversation') {
  const now = new Date().toISOString();
  return {
    id: `session-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
    title,
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

/**
 * Provides multi-session chat history state + actions to the entire app.
 * Persisted in localStorage.
 */
export function ChatProvider({ children }) {
  const [sessions, setSessions] = useLocalStorage('poseidon-chat-sessions', []);
  const [activeSessionId, setActiveSessionId] = useLocalStorage('poseidon-active-session-id', '');
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedTurn, setSelectedTurn] = useState(null);
  const abortControllerRef = useRef(null);
  
  // Overview Drawer State (Right)
  const [isOverviewOpen, setIsOverviewOpen] = useLocalStorage('poseidon-overview-open', false);
  const [overviewTab, setOverviewTab] = useState('trajectory'); // 'trajectory' | 'topology' | 'security'

  // History Drawer State (Left)
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Legacy Migration & Initial Setup
  useEffect(() => {
    // If no sessions exist yet, check for legacy poseidon-chat-messages
    if (!sessions || sessions.length === 0) {
      let legacyMessages = [];
      try {
        const stored = localStorage.getItem('poseidon-chat-messages');
        if (stored) legacyMessages = JSON.parse(stored);
      } catch (e) {
        // ignore parse error
      }

      const initialSession = createNewSessionObject(
        legacyMessages.length > 0 ? (legacyMessages[0]?.content?.slice(0, 30) || 'Previous Session') : 'New Conversation'
      );
      initialSession.messages = legacyMessages;

      setSessions([initialSession]);
      setActiveSessionId(initialSession.id);
    } else if (!activeSessionId || !sessions.some((s) => s.id === activeSessionId)) {
      setActiveSessionId(sessions[0].id);
    }
  }, []);

  // Get active session
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0] || null;
  const messages = activeSession ? activeSession.messages : [];

  const idCounter = useRef(Date.now());

  const nextId = () => {
    idCounter.current += 1;
    return `msg-${idCounter.current}`;
  };

  // Create a fresh session and switch to it immediately
  const createNewSession = useCallback(() => {
    const newSession = createNewSessionObject('New Conversation');
    setActiveSessionId(newSession.id);
    setSessions((prev) => {
      const validPrev = Array.isArray(prev) ? prev : [];
      // Keep sessions that have messages, discarding any abandoned blank sessions
      const withMessages = validPrev.filter((s) => s.messages && s.messages.length > 0);
      return [newSession, ...withMessages];
    });
    setError(null);
    return newSession.id;
  }, [setActiveSessionId, setSessions]);

  // Switch to an existing session (pruning any unused blank session)
  const switchSession = useCallback((sessionId) => {
    if (sessions.some((s) => s.id === sessionId)) {
      setActiveSessionId(sessionId);
      setError(null);
    }
  }, [sessions, setActiveSessionId]);

  // Delete a session
  const deleteSession = useCallback((sessionId) => {
    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessionId);
      if (filtered.length === 0) {
        const fresh = createNewSessionObject('New Conversation');
        setActiveSessionId(fresh.id);
        return [fresh];
      }
      if (sessionId === activeSessionId) {
        setActiveSessionId(filtered[0].id);
      }
      return filtered;
    });
  }, [activeSessionId, setSessions, setActiveSessionId]);

  // Rename a session
  const renameSession = useCallback((sessionId, newTitle) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle, updatedAt: new Date().toISOString() } : s))
    );
  }, [setSessions]);

  // Clear all history
  const clearAllHistory = useCallback(() => {
    const fresh = createNewSessionObject('New Conversation');
    setSessions([fresh]);
    setActiveSessionId(fresh.id);
    setError(null);
  }, [setSessions, setActiveSessionId]);

  // Send message in current active session
  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;

    // Abort any previous inflight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Ensure we have an active session
    let targetSessionId = activeSessionId;
    if (!targetSessionId || !sessions.some((s) => s.id === targetSessionId)) {
      targetSessionId = createNewSession();
    }

    const userMessage = {
      id: nextId(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };

    // Update session with user message + auto-generate title if it's the first message
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== targetSessionId) return s;

        const updatedMessages = [...s.messages, userMessage];
        const newTitle =
          s.messages.length === 0 || s.title === 'New Conversation'
            ? text.trim().slice(0, 32) + (text.trim().length > 32 ? '...' : '')
            : s.title;

        return {
          ...s,
          title: newTitle,
          updatedAt: new Date().toISOString(),
          messages: updatedMessages,
        };
      })
    );

    setIsLoading(true);
    setError(null);

    try {
      const data = await sendChatMessage(text.trim(), 'local_user', controller.signal);

      const agentMessage = {
        id: nextId(),
        role: 'agent',
        content: data.reply,
        runId: data.run_id,
        approvalRequest: data.approval_request || null,
        activeAgent: data.active_agent || 'poseidon',
        memoryContext: data.memory_context || null,
        trajectory: data.trajectory || [],
        timestamp: new Date().toISOString(),
      };

      setSelectedTurn(agentMessage);

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== targetSessionId) return s;
          return {
            ...s,
            updatedAt: new Date().toISOString(),
            messages: [...s.messages, agentMessage],
          };
        })
      );
    } catch (err) {
      if (err.name === 'AbortError' || controller.signal.aborted) {
        // User clicked stop
        const stoppedMessage = {
          id: nextId(),
          role: 'agent',
          content: '⏹ *Generation stopped by user.*',
          timestamp: new Date().toISOString(),
        };

        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== targetSessionId) return s;
            return {
              ...s,
              updatedAt: new Date().toISOString(),
              messages: [...s.messages, stoppedMessage],
            };
          })
        );
        return;
      }

      const isConnectionError =
        err.message === 'Failed to fetch' ||
        err.message?.includes('NetworkError') ||
        err.message?.includes('Failed to connect');

      const errorText = isConnectionError
        ? 'Could not connect to the backend server. Is FastAPI running on http://127.0.0.1:8000?'
        : err.message || 'Something went wrong.';

      setError(errorText);

      const errorMessage = {
        id: nextId(),
        role: 'agent',
        content: `⚠ **Error:** ${errorText}`,
        isError: true,
        timestamp: new Date().toISOString(),
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== targetSessionId) return s;
          return {
            ...s,
            updatedAt: new Date().toISOString(),
            messages: [...s.messages, errorMessage],
          };
        })
      );
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setIsLoading(false);
    }
  }, [isLoading, activeSessionId, sessions, createNewSession, setSessions]);

  // Stop active generation
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  }, []);

  const handleApprovalDecision = useCallback(
    async (approvalId, decision) => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await sendApprovalDecision(approvalId, decision);
        const agentMessage = {
          id: nextId(),
          role: 'agent',
          content: data.reply,
          runId: data.run_id,
          approvalRequest: data.approval_request || null,
          activeAgent: data.active_agent || 'poseidon',
          memoryContext: data.memory_context || null,
          trajectory: data.trajectory || [],
          timestamp: new Date().toISOString(),
        };
        setSelectedTurn(agentMessage);
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== activeSessionId) return s;
            return {
              ...s,
              updatedAt: new Date().toISOString(),
              messages: [...s.messages, agentMessage],
            };
          })
        );
      } catch (err) {
        setError(err.message || 'Failed to submit approval decision');
      } finally {
        setIsLoading(false);
      }
    },
    [activeSessionId, setSessions]
  );

  const inspectTurn = useCallback((msg) => {
    setSelectedTurn(msg);
    setIsOverviewOpen(true);
  }, [setIsOverviewOpen]);

  const clearChat = useCallback(() => {
    createNewSession();
  }, [createNewSession]);

  // Overview Controls
  const toggleOverview = useCallback(() => {
    setIsOverviewOpen((prev) => !prev);
  }, [setIsOverviewOpen]);

  const openOverview = useCallback((tab = 'trajectory') => {
    setOverviewTab(tab);
    setIsOverviewOpen(true);
  }, [setOverviewTab, setIsOverviewOpen]);

  const closeOverview = useCallback(() => {
    setIsOverviewOpen(false);
  }, [setIsOverviewOpen]);

  // History Controls
  const toggleHistory = useCallback(() => {
    setIsHistoryOpen((prev) => !prev);
  }, []);

  const openHistory = useCallback(() => {
    setIsHistoryOpen(true);
  }, []);

  const closeHistory = useCallback(() => {
    setIsHistoryOpen(false);
  }, []);

  const value = {
    sessions,
    activeSessionId,
    activeSession,
    messages,
    isLoading,
    error,

    // Session Actions
    createNewSession,
    switchSession,
    deleteSession,
    renameSession,
    clearAllHistory,
    sendMessage,
    stopGeneration,
    clearChat,
    handleApprovalDecision,
    selectedTurn,
    inspectTurn,

    // Overview Drawer
    isOverviewOpen,
    overviewTab,
    setOverviewTab,
    toggleOverview,
    openOverview,
    closeOverview,

    // History Drawer
    isHistoryOpen,
    toggleHistory,
    openHistory,
    closeHistory,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}

/**
 * Hook to access chat state and actions.
 * Must be used inside a <ChatProvider>.
 */
export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return ctx;
}

export default ChatContext;

