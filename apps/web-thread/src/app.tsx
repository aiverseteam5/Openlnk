/**
 * Web-thread PWA — single-screen receipt view.
 *
 * DESIGN.md: Receipt at top, action buttons middle, chat input bottom.
 * No router, no design-system imports, hand-rolled Tailwind only.
 * Performance budget: ≤120KB gzip total JS+CSS.
 */

import { useState, useEffect } from "preact/hooks";

// API base — no design-system imports for bundle size
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

// State color map (inline — no design-system import for bundle size)
const STATE_COLORS: Record<
  string,
  { text: string; bg: string; bar: string; label: string }
> = {
  proposed: { text: "#374151", bg: "#F3F4F6", bar: "#374151", label: "PROPOSED" },
  accepted: { text: "#1A6B3C", bg: "#EAF4EE", bar: "#1A6B3C", label: "ACCEPTED" },
  in_progress: { text: "#1A6B3C", bg: "#EAF4EE", bar: "#1A6B3C", label: "IN PROGRESS" },
  overdue: { text: "#92600A", bg: "#FDF4E3", bar: "#92600A", label: "OVERDUE" },
  broken: { text: "#B91C1C", bg: "#FEF2F2", bar: "#B91C1C", label: "BROKEN" },
  fulfilled: { text: "#1A6B3C", bg: "#EAF4EE", bar: "#1A6B3C", label: "FULFILLED" },
  cancelled: { text: "#6B6456", bg: "#F5F2EC", bar: "#D6D0C4", label: "CANCELLED" },
};

interface Commitment {
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
}

function formatAmount(paise: number | null, currency: string): string {
  if (paise === null) return "";
  const amt = paise / 100;
  if (currency === "INR") return `\u20B9${amt.toLocaleString("en-IN")}`;
  return `${currency} ${amt.toFixed(2)}`;
}

function formatDue(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

function CommitmentReceipt({ c }: { c: Commitment }) {
  const stateKey = c.at_risk ? "overdue" : c.state;
  const sc = STATE_COLORS[stateKey] ?? STATE_COLORS.proposed;

  return (
    <div class="flex border border-border rounded-[2px] bg-surface overflow-hidden">
      {/* 3px state bar */}
      <div class="w-[3px] shrink-0" style={{ backgroundColor: sc.bar }} />

      <div class="flex-1 px-3 py-2.5">
        {/* ID + State badge */}
        <div class="flex justify-between items-center mb-1">
          <span class="font-mono text-[10px] text-text-muted">
            CMT-{c.id.slice(0, 4).toUpperCase()}
          </span>
          <span
            class="font-mono text-[11px] font-semibold tracking-[0.1em] px-2 py-0.5 rounded-full"
            style={{ color: sc.text, backgroundColor: sc.bg }}
          >
            {sc.label}
          </span>
        </div>

        {/* Title */}
        <h2 class="text-sm font-semibold leading-5 mb-1 truncate">{c.title}</h2>

        {/* Class + Amount */}
        <div class="flex justify-between items-center">
          <span class="text-xs text-text-muted">{c.class}</span>
          {c.amount_paise !== null && (
            <span class="font-mono text-[15px] font-semibold leading-5">
              {formatAmount(c.amount_paise, c.currency)}
            </span>
          )}
        </div>

        {/* Due date */}
        {c.due_at && (
          <div class="flex justify-end mt-1">
            <span class="font-mono text-[11px] text-text-muted">
              Due {formatDue(c.due_at)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function ActionButtons({
  state,
  onAction,
}: {
  state: string;
  onAction: (action: string) => void;
}) {
  if (state === "proposed") {
    return (
      <div class="flex gap-2 my-3">
        <button
          class="flex-1 py-2.5 bg-accent text-white font-medium text-sm rounded-[4px] hover:bg-accent-hover"
          onClick={() => onAction("accepted")}
        >
          Accept
        </button>
        <button
          class="flex-1 py-2.5 border border-border text-text-primary font-medium text-sm rounded-[4px]"
          onClick={() => onAction("cancelled")}
        >
          Reject
        </button>
      </div>
    );
  }
  if (state === "accepted") {
    return (
      <div class="flex gap-2 my-3">
        <button
          class="flex-1 py-2.5 bg-accent text-white font-medium text-sm rounded-[4px] hover:bg-accent-hover"
          onClick={() => onAction("in_progress")}
        >
          Mark In Progress
        </button>
      </div>
    );
  }
  if (state === "in_progress") {
    return (
      <div class="flex gap-2 my-3">
        <button
          class="flex-1 py-2.5 bg-accent text-white font-medium text-sm rounded-[4px] hover:bg-accent-hover"
          onClick={() => onAction("done")}
        >
          Mark Done
        </button>
      </div>
    );
  }
  return null;
}

/** Persist token in localStorage for session continuity (OL-082). */
function persistSession(token: string): void {
  try {
    localStorage.setItem("openlnk_thread_token", token);
  } catch {
    // localStorage unavailable in some webviews — silent fallback
  }
}

function getPersistedToken(): string | null {
  try {
    return localStorage.getItem("openlnk_thread_token");
  } catch {
    return null;
  }
}

export function App() {
  const [commitment, setCommitment] = useState<Commitment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState("");

  // Extract token from URL path: /t/{token}
  const urlToken = window.location.pathname.split("/t/")[1] ?? "";
  const token = urlToken || getPersistedToken() || "";

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    persistSession(token);

    fetch(`${API_BASE}/threads/resolve/${encodeURIComponent(token)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.json();
      })
      .then((data: { commitments: Commitment[] }) => {
        if (data.commitments.length > 0) {
          setCommitment(data.commitments[0]);
        }
        setLoading(false);
      })
      .catch(() => {
        setError("Link expired or invalid.");
        setLoading(false);
      });
  }, [token]);

  const handleAction = (newState: string) => {
    if (!commitment) return;
    setCommitment({ ...commitment, state: newState });

    // Optimistic update — fire and forget state transition
    fetch(`${API_BASE}/threads/resolve/${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: newState, version: commitment.version }),
    }).catch(() => {
      // Revert on failure
      setCommitment(commitment);
    });
  };

  return (
    <div class="max-w-md mx-auto min-h-screen flex flex-col bg-bg">
      {/* Header */}
      <header class="px-4 py-3 border-b border-border">
        <span class="font-mono text-[13px] font-semibold tracking-[0.08em] text-accent">
          OPENLNK
        </span>
      </header>

      {/* Content */}
      <main class="flex-1 px-4 py-3">
        {loading && (
          <p class="text-text-muted text-sm text-center py-8">
            {"\u2014"} Loading...
          </p>
        )}

        {!loading && error && (
          <p class="text-text-muted text-sm font-medium text-center py-8">
            {error}
          </p>
        )}

        {!loading && !error && !commitment && (
          <p class="text-text-muted text-sm font-medium text-center py-8">
            No commitment found.
          </p>
        )}

        {!loading && commitment && (
          <>
            <CommitmentReceipt c={commitment} />
            <ActionButtons state={commitment.state} onAction={handleAction} />
          </>
        )}
      </main>

      {/* Chat input — always visible (DESIGN.md) */}
      <footer class="border-t border-border px-4 py-2">
        <div class="flex gap-2">
          <input
            type="text"
            class="flex-1 px-3 py-2 text-sm border border-border rounded-[2px] bg-surface outline-none focus:border-accent"
            placeholder="Type a message..."
            value={chatInput}
            onInput={(e) => setChatInput((e.target as HTMLInputElement).value)}
          />
          <button
            class="px-4 py-2 bg-accent text-white text-sm font-medium rounded-[4px] hover:bg-accent-hover"
            onClick={() => setChatInput("")}
          >
            Send
          </button>
        </div>
      </footer>
    </div>
  );
}
