import { api } from './client';

export async function fetchSemanticMemory(userId = 'local_user', query = null) {
  const q = query ? `&query=${encodeURIComponent(query)}` : '';
  return api(`/memory/semantic?user_id=${encodeURIComponent(userId)}${q}`);
}

export async function fetchEpisodicMemory(userId = 'local_user', limit = 50) {
  return api(`/memory/episodic?user_id=${encodeURIComponent(userId)}&limit=${limit}`);
}

export async function fetchProceduralMemory() {
  return api('/memory/procedural');
}

export async function fetchMemoryStatus(userId = 'local_user') {
  return api(`/memory/status?user_id=${encodeURIComponent(userId)}`);
}

export async function triggerConsolidation(userId = 'local_user', force = true) {
  return api('/memory/consolidate', {
    method: 'POST',
    body: { user_id: userId, force },
  });
}
