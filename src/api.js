const BASE = import.meta.env.VITE_API_URL || '';
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

async function request(path, options = {}, accessToken = '') {
  let res;
  try {
    const headers = new Headers(options.headers || {});
    const sessionAuth = authHeader();

    if (!headers.has('Authorization')) {
      if (accessToken) {
        headers.set('Authorization', `Bearer ${accessToken}`);
      } else if (sessionAuth.Authorization) {
        headers.set('Authorization', sessionAuth.Authorization);
      }
    }

    res = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error('Cannot reach the server. Check that the backend is running.');
  }
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : body.detail?.message;
    } catch { /* non-JSON error body */ }
    throw new Error(detail || `The server returned an error (${res.status}).`);
  }

  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * Hand-off to Member 2. POST /api/generate with:
 * { source_text, source_type, source_filename, output_types[], audience, tone,
 *   language, detail_level, objective }
 * Expected response:
 * { outputs: [{ output_type, title, summary, key_points: string[], body }] }
 */
export async function generate(payload, accessToken) {
  if (USE_MOCK) return mockGenerate(payload);
  return request('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(payload),
  }, accessToken);
}

export async function identifyAccessToken(accessToken) {
  if (USE_MOCK) return { role: 'reviewer' };
  return request('/api/v1/auth/me', {}, accessToken);
}

export async function listGenerations(accessToken) {
  if (USE_MOCK) return [];
  const result = await request('/api/v1/generations', {}, accessToken);
  return result.generations;
}

export async function getGeneration(generationId, accessToken) {
  return request(`/api/v1/generations/${encodeURIComponent(generationId)}`, {}, accessToken);
}

export async function updateOutput(outputId, output, accessToken) {
  return request(`/api/v1/outputs/${encodeURIComponent(outputId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(output),
  }, accessToken);
}

export async function approveOutput(outputId, accessToken) {
  return request(`/api/v1/outputs/${encodeURIComponent(outputId)}/approve`, { method: 'POST' }, accessToken);
}

export async function recordExport(outputId, accessToken) {
  return request(`/api/v1/outputs/${encodeURIComponent(outputId)}/export`, { method: 'POST' }, accessToken);
}

export async function exportPresentationPptx(outputId, accessToken) {
  let response;
  try {
    response = await fetch(
      `${BASE}/api/v1/outputs/${encodeURIComponent(outputId)}/presentation.pptx`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
      },
    );
  } catch {
    throw new Error('Cannot reach the server. Check that the backend is running.');
  }
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : body.detail?.message;
    } catch { /* non-JSON error body */ }
    throw new Error(detail || `The server returned an error (${response.status}).`);
  }
  return {
    blob: await response.blob(),
    filename: response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1]
      || 'formax-presentation.pptx',
  };
}

export async function getOutputVideoJob(outputId, accessToken) {
  const result = await request(
    `/api/v1/outputs/${encodeURIComponent(outputId)}/video`,
    {},
    accessToken,
  );
  return result.job;
}

export async function startVideoGeneration(outputId, accessToken) {
  return request(
    `/api/v1/outputs/${encodeURIComponent(outputId)}/video`,
    { method: 'POST' },
    accessToken,
  );
}

export async function getVideoJob(videoJobId, accessToken) {
  return request(`/api/v1/video-jobs/${encodeURIComponent(videoJobId)}`, {}, accessToken);
}

export async function fetchVideoDownload(videoJobId, accessToken) {
  let response;
  try {
    response = await fetch(
      `${BASE}/api/v1/video-jobs/${encodeURIComponent(videoJobId)}/download`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );
  } catch {
    throw new Error('Cannot reach the server. Check that the backend is running.');
  }
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : body.detail?.message;
    } catch { /* non-JSON error body */ }
    throw new Error(detail || `The server returned an error (${response.status}).`);
  }
  return response.blob();
}

async function mockGenerate(p) {
  await new Promise((r) => setTimeout(r, 1200));
  const snippet = p.source_text.slice(0, 280);
  return {
    outputs: p.output_types.map((t) => ({
      output_type: t,
      title: `Sample ${t.replace('_', ' ')} (mock)`,
      summary: `Mock draft for ${p.audience}, ${p.tone} tone, in ${p.language}.`,
      key_points: ['First key point from the source', 'Second key point', 'Third key point'],
      body: snippet + (p.source_text.length > 280 ? '...' : ''),
    })),
  };
}

function authHeader() {
  try {
    const t = sessionStorage.getItem('formax_token');
    return t && t !== 'mock-token' ? { Authorization: `Bearer ${t}` } : {};
  } catch { return {}; }
}

export async function login(email, password) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 600));
    return 'mock-token';
  }
  let res;
  try {
    res = await fetch(`${BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error('Cannot reach the server. Check that the backend is running.');
  }
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).detail; } catch { /* non-JSON body */ }
    throw new Error(detail || 'Sign in failed. Check your email and password.');
  }
  return (await res.json()).token;
}