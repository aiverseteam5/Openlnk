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
  updated_at: string;
  provenance_kind: string | null;
  extraction_confidence: number | null;
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
  principalId: string;
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

  const res = await fetch(url.toString(), {
    headers: { "X-Principal-Id": params.principalId },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<CursorPage>;
}

export async function fetchCommitment(
  principalId: string,
  id: string,
): Promise<Commitment> {
  const res = await fetch(`${API_BASE}/v1/commitments/${id}`, {
    headers: { "X-Principal-Id": principalId },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Commitment>;
}

export async function transitionState(
  principalId: string,
  id: string,
  newState: string,
  version: number,
): Promise<Commitment> {
  const res = await fetch(`${API_BASE}/v1/commitments/${id}/transition`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Principal-Id": principalId,
    },
    body: JSON.stringify({ state: newState, version }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Commitment>;
}

export async function fetchContexts(principalId: string): Promise<Context[]> {
  const res = await fetch(`${API_BASE}/v1/contexts`, {
    headers: { "X-Principal-Id": principalId },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Context[]>;
}

export async function correctCommitment(
  principalId: string,
  id: string,
  body: { action: string; edits?: Record<string, unknown> },
): Promise<Commitment> {
  const res = await fetch(`${API_BASE}/v1/commitments/${id}/correct`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Principal-Id": principalId,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Commitment>;
}

export interface AuditEntry {
  id: number;
  at: string;
  actor_kind: string;
  event: string;
  detail: Record<string, unknown>;
}

export async function fetchCommitmentHistory(
  principalId: string,
  id: string,
): Promise<AuditEntry[]> {
  const res = await fetch(`${API_BASE}/v1/commitments/${id}/history`, {
    headers: { "X-Principal-Id": principalId },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<AuditEntry[]>;
}
