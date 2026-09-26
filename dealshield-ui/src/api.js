/**
 * DealShield API Client
 * All fetch calls to the FastAPI backend.
 */

const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API Error ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request('/health'),

  graphStats: () => request('/graph/stats'),

  analyzeCoc: (targetCompany) =>
    request('/analyze/coc', {
      method: 'POST',
      body: JSON.stringify({ target_company: targetCompany }),
    }),

  analyzeSecondary: (targetCompany) =>
    request('/analyze/secondary', {
      method: 'POST',
      body: JSON.stringify({ target_company: targetCompany }),
    }),

  scoreRisk: (payload) =>
    request('/analyze/score', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  runFullPipeline: (targetCompany) =>
    request('/analyze/full', {
      method: 'POST',
      body: JSON.stringify({ target_company: targetCompany }),
    }),

  graphQuery: (query) =>
    request('/graph/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),

  graphPresets: () => request('/graph/presets'),
};
