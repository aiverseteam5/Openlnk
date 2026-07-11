/**
 * API client — fetch-based, same interface as web-owner.
 *
 * Cursor pagination (CLAUDE.md: cursor pagination only).
 * Runtime boundary: will add zod validation when api-client types are generated.
 */

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Commitment {
  id: string;
  title: string;
  class: string;
  state: string;
  amount_paise: number | null;
  currency: string;
  due_at: string | null;
  at_risk: boolean;
  owner_id: string;
  counterparty_id: string | null;
  version: number;
  context_id: string;
  created_at: string;
}

export interface CursorPage {
  items: Commitment[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface Context {
  id: string;
  type: string;
  label: string;
}

export async function fetchCommitments(params: {
  state?: string;
  contextId?: string;
  cursor?: string;
  limit?: number;
}): Promise<CursorPage> {
  const url = new URL(`${API_BASE}/v1/commitments`);
  if (params.state) url.searchParams.set("state", params.state);
  if (params.contextId) url.searchParams.set("context_id", params.contextId);
  if (params.cursor) url.searchParams.set("cursor", params.cursor);
  if (params.limit) url.searchParams.set("limit", String(params.limit));

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<CursorPage>;
}

export async function fetchCommitment(id: string): Promise<Commitment> {
  const res = await fetch(`${API_BASE}/v1/commitments/${id}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Commitment>;
}

export async function transitionState(
  id: string,
  newState: string,
  version: number,
): Promise<Commitment> {
  const res = await fetch(`${API_BASE}/v1/commitments/${id}/transition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state: newState, version }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Commitment>;
}

export async function fetchContexts(): Promise<Context[]> {
  const res = await fetch(`${API_BASE}/v1/contexts`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Context[]>;
}
