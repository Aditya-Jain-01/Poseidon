/**
 * Agents and Settings API calls for Person C.
 */
import { api } from './client';

export async function fetchAgents() {
  return api('/agents');
}

export async function fetchAgent(agentId) {
  return api(`/agents/${agentId}`);
}

export async function createAgent(agentData) {
  return api('/agents', {
    method: 'POST',
    body: agentData,
  });
}

export async function updateAgent(agentId, updates) {
  return api(`/agents/${agentId}`, {
    method: 'PUT',
    body: updates,
  });
}

export async function deleteAgent(agentId) {
  return api(`/agents/${agentId}`, {
    method: 'DELETE',
  });
}

export async function reloadAgents() {
  return api('/agents/reload', {
    method: 'POST',
  });
}

export async function fetchLLMSettings() {
  return api('/settings/llm');
}

export async function updateLLMSettings(agentId, settingsData) {
  return api(`/settings/llm/${agentId}`, {
    method: 'PUT',
    body: settingsData,
  });
}

export async function checkLLMHealth(agentId) {
  return api(`/settings/llm/check/${agentId}`);
}

export async function fetchTrajectory(runId) {
  return api(`/runs/${runId}/trajectory`);
}
