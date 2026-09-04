import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  fetchAgents,
  fetchLLMSettings,
  createAgent as apiCreateAgent,
  updateAgent as apiUpdateAgent,
  deleteAgent as apiDeleteAgent,
  reloadAgents as apiReloadAgents,
  updateLLMSettings as apiUpdateLLMSettings,
  checkLLMHealth as apiCheckLLMHealth,
} from '../api/agents';

export const AgentContext = createContext(null);

export function AgentProvider({ children }) {
  const [agents, setAgents] = useState([]);
  const [activeAgentId, setActiveAgentId] = useState('poseidon');
  const [llmSettings, setLlmSettings] = useState({ providers: {}, agent_overrides: {}, agents: {} });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [healthStatus, setHealthStatus] = useState({}); // { [agentId]: { status: 'online' | 'offline' | 'checking', message, model } }

  const loadAgents = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchAgents();
      if (Array.isArray(data)) {
        setAgents(data);
        if (data.length > 0 && !data.some((a) => a.id === activeAgentId)) {
          setActiveAgentId(data[0].id);
        }
      }
    } catch (err) {
      console.error('[AgentContext] Error fetching agents:', err);
      setError(err.message || 'Failed to load agents');
    }
  }, [activeAgentId]);

  const loadLLM = useCallback(async () => {
    try {
      const data = await fetchLLMSettings();
      if (data) {
        setLlmSettings(data);
      }
    } catch (err) {
      console.error('[AgentContext] Error fetching LLM settings:', err);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setIsLoading(true);
    await Promise.all([loadAgents(), loadLLM()]);
    setIsLoading(false);
  }, [loadAgents, loadLLM]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  const createAgent = useCallback(async (agentData) => {
    setIsLoading(true);
    setError(null);
    try {
      const created = await apiCreateAgent(agentData);
      await refreshAll();
      return created;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refreshAll]);

  const updateAgent = useCallback(async (agentId, updates) => {
    setIsLoading(true);
    setError(null);
    try {
      const updated = await apiUpdateAgent(agentId, updates);
      await refreshAll();
      return updated;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refreshAll]);

  const deleteAgent = useCallback(async (agentId) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiDeleteAgent(agentId);
      await refreshAll();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refreshAll]);

  const reloadFromDisk = useCallback(async () => {
    setIsLoading(true);
    try {
      await apiReloadAgents();
      await refreshAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [refreshAll]);

  const updateLLMProvider = useCallback(async (agentId, settingsData) => {
    try {
      const updated = await apiUpdateLLMSettings(agentId, settingsData);
      await loadLLM();
      return updated;
    } catch (err) {
      console.error('[AgentContext] Error updating LLM provider:', err);
      throw err;
    }
  }, [loadLLM]);

  const checkAgentHealth = useCallback(async (agentId) => {
    setHealthStatus((prev) => ({
      ...prev,
      [agentId]: { status: 'checking', message: 'Testing connectivity...' },
    }));
    try {
      const res = await apiCheckLLMHealth(agentId);
      setHealthStatus((prev) => ({
        ...prev,
        [agentId]: {
          status: res.available ? 'online' : 'offline',
          message: res.message || (res.available ? 'Connected' : 'Unreachable'),
          model: res.model,
          base_url: res.base_url,
        },
      }));
      return res;
    } catch (err) {
      setHealthStatus((prev) => ({
        ...prev,
        [agentId]: {
          status: 'offline',
          message: err.message || 'Connection check failed',
        },
      }));
      return { available: false, message: err.message };
    }
  }, []);

  const testAllConnections = useCallback(async () => {
    if (!agents || agents.length === 0) return;
    const promises = agents.map((a) => checkAgentHealth(a.id));
    await Promise.allSettled(promises);
  }, [agents, checkAgentHealth]);

  const activeAgent = agents.find((a) => a.id === activeAgentId) || agents[0] || null;
  const customAgentCount = agents.filter((a) => !a.is_prebuilt).length;
  const canCreateCustom = customAgentCount < 2;

  const value = {
    agents,
    activeAgentId,
    setActiveAgentId,
    activeAgent,
    customAgentCount,
    canCreateCustom,
    llmSettings,
    isLoading,
    error,
    healthStatus,
    loadAgents,
    loadLLM,
    refreshAll,
    createAgent,
    updateAgent,
    deleteAgent,
    reloadFromDisk,
    updateLLMProvider,
    checkAgentHealth,
    testAllConnections,
  };

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
}

export function useAgents() {
  const ctx = useContext(AgentContext);
  if (!ctx) {
    throw new Error('useAgents must be used within an AgentProvider');
  }
  return ctx;
}

export default AgentContext;
