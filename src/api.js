const BASE = import.meta.env.VITE_API_URL || '';
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

/**
 * Hand-off to Member 2. POST /api/generate with:
 * { source_text, source_type, source_filename, output_types[], audience, tone,
 *   language, detail_level, objective }
 * Expected response:
 * { outputs: [{ output_type, title, summary, key_points: string[], body }] }
 */
export async function generate(payload) {
  if (USE_MOCK) return mockGenerate(payload);

  let res;
  try {
    res = await fetch(`${BASE}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error('Cannot reach the server. Check that the backend is running.');
  }
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).detail; } catch { /* non-JSON error body */ }
    throw new Error(detail || `The server returned an error (${res.status}).`);
  }
  return res.json();
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
