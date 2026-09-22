const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:4000';

/**
 * POST /api/recommend — multimodal outfit recommendation
 * @param {{ query: string, gender?: string, occasion?: string, budget?: string }} payload
 * @returns {Promise<{ outfits: Array, explanation?: string }>}
 */
export async function recommendOutfits(payload) {
  const res = await fetch(`${API_BASE}/api/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.error || body?.message) {
        message = body.error || body.message;
      }
    } catch {
      /* ignore parse errors */
    }
    throw new Error(message);
  }

  return res.json();
}

export { API_BASE };
