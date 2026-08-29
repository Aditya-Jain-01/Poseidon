import React, { createContext, useContext, useCallback, useRef } from 'react';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { sendChatMessage } from '../api/chat';

export const ChatContext = createContext(null);

/**
 * Provides chat state + actions to the entire app.
 * Messages, dock open state, and dock width are persisted to localStorage.
 */
export function ChatProvider({ children }) {
  const [messages, setMessages] = useLocalStorage('poseidon-chat-messages', []);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [isDockOpen, setIsDockOpen] = useLocalStorage('poseidon-dock-open', true);
  const [dockWidth, setDockWidth] = useLocalStorage('poseidon-dock-width', 420);
  const [isExpanded, setIsExpanded] = useLocalStorage('poseidon-dock-expanded', false);
  const idCounter = useRef(Date.now());

  const nextId = () => {
    idCounter.current += 1;
    return `msg-${idCounter.current}`;
  };

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;

    const userMessage = {
      id: nextId(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const data = await sendChatMessage(text.trim());

      const agentMessage = {
        id: nextId(),
        role: 'agent',
        content: data.reply,
        runId: data.run_id,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err) {
      setError(err.message || 'Failed to send message');

      const errorMessage = {
        id: nextId(),
        role: 'agent',
        content: `⚠ **Error:** ${err.message || 'Something went wrong. Is the backend running?'}`,
        isError: true,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, setMessages]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, [setMessages]);

  const toggleDock = useCallback(() => {
    setIsDockOpen((prev) => !prev);
  }, [setIsDockOpen]);

  const toggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, [setIsExpanded]);

  const updateDockWidth = useCallback((newWidth) => {
    // Constrain width between 340px and max 1100px / 80vw
    const constrained = Math.max(340, Math.min(newWidth, window.innerWidth * 0.8));
    setDockWidth(constrained);
  }, [setDockWidth]);

  const value = {
    messages,
    isLoading,
    error,
    isDockOpen,
    dockWidth,
    isExpanded,
    sendMessage,
    clearChat,
    toggleDock,
    toggleExpand,
    setDockWidth: updateDockWidth,
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
