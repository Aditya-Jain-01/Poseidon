import { api } from './client';

export const fetchBrainStatus = () => api('/brain/status');
export const fetchBrainNodes = () => api('/brain/nodes');
export const fetchBrainGraph = () => api('/brain/graph');
export const fetchBrainNode = (id) => api(`/brain/nodes/${encodeURIComponent(id)}`);
export const syncBrain = () => api('/brain/sync', { method: 'POST', timeout: 120000 });
export const queryBrain = (question) => api('/brain/query', { method: 'POST', body: { question }, timeout: 120000 });
export const lintBrain = () => api('/brain/lint', { method: 'POST' });
export const addBrainSource = (title, text) => api('/brain/sources', { method: 'POST', body: { title, text }, timeout: 120000 });
