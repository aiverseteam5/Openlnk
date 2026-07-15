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

function getAuthHeaders(principalId: string): Record<string, string> {
  // Try SecureStore token via store; fall back to X-Principal-Id
  // Note: actual token is read synchronously from store state
  const { useAppStore } = require("@/store/app");
  const accessToken = useAppStore.getState().accessToken;
  if (accessToken) {
    return { Authorization: `Bearer ${accessToken}` };
  }
  return { "X-Principal-Id": principalId };
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
    headers: getAuthHeaders(params.principalId),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<CursorPage>;
}

export async function fetchCommitment(
  principalId: string,
  id: string,
): Promise<Commitment> {
  const res = await fetch(`${API_BASE}/v1/commitments/${id}`, {
    headers: getAuthHeaders(principalId),
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
      ...getAuthHeaders(principalId),
    },
    body: JSON.stringify({ state: newState, version }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Commitment>;
}

export async function fetchContexts(principalId: string): Promise<Context[]> {
  const res = await fetch(`${API_BASE}/v1/contexts`, {
    headers: getAuthHeaders(principalId),
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
      ...getAuthHeaders(principalId),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<Commitment>;
}

// ── Daily Brief ──

export interface BriefCounts {
  at_risk: number;
  due_today: number;
  proposed: number;
  done_today: number;
  total_active: number;
}

export interface BriefSummaryResponse {
  summary: string;
  counts: BriefCounts;
  generated_at: string;
}

export async function fetchBriefSummary(
  principalId: string,
): Promise<BriefSummaryResponse> {
  const res = await fetch(`${API_BASE}/v1/brief/summary`, {
    headers: getAuthHeaders(principalId),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<BriefSummaryResponse>;
}

// ── Learning Profile ──

export interface LearningProfile {
  preferred_nudge_hour: number | null;
  suggested_quiet_hours: { start_hour: number; end_hour: number } | null;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  data_points: number;
}

export async function fetchLearningProfile(
  principalId: string,
): Promise<LearningProfile> {
  const res = await fetch(`${API_BASE}/v1/me/learning-profile`, {
    headers: getAuthHeaders(principalId),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<LearningProfile>;
}

export async function updateQuietHours(
  principalId: string,
  start: string,
  end: string,
): Promise<LearningProfile> {
  const res = await fetch(`${API_BASE}/v1/me/quiet-hours`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(principalId),
    },
    body: JSON.stringify({ start, end }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<LearningProfile>;
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
    headers: getAuthHeaders(principalId),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<AuditEntry[]>;
}
