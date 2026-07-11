/**
 * Web-thread PWA — single-screen receipt view.
 *
 * DESIGN.md: Receipt at top, action buttons middle, chat input bottom.
 * No router, no design-system imports, hand-rolled Tailwind only.
 * Performance budget: ≤120KB gzip total JS+CSS.
 */

import { useState, useEffect, useRef } from "preact/hooks";

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

/** Track funnel events (OL-085). Fire-and-forget to API. */
function trackFunnel(event: "open" | "return"): void {
  const token = getPersistedToken();
  if (!token) return;
  fetch(`${API_BASE}/threads/funnel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_type: event, token }),
  }).catch(() => {
    /* non-critical — silent fail */
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
  pending,
}: {
  state: string;
  onAction: (action: string) => void;
  pending: boolean;
}) {
  if (state === "proposed") {
    return (
      <div class="flex gap-2 my-3">
        <button
          class="flex-1 py-2.5 bg-accent text-white font-medium text-sm rounded-[4px] hover:bg-accent-hover disabled:opacity-50"
          disabled={pending}
          onClick={() => onAction("accepted")}
        >
          Accept
        </button>
        <button
          class="flex-1 py-2.5 border border-border text-text-primary font-medium text-sm rounded-[4px] disabled:opacity-50"
          disabled={pending}
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
          class="flex-1 py-2.5 bg-accent text-white font-medium text-sm rounded-[4px] hover:bg-accent-hover disabled:opacity-50"
          disabled={pending}
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
          class="flex-1 py-2.5 bg-accent text-white font-medium text-sm rounded-[4px] hover:bg-accent-hover disabled:opacity-50"
          disabled={pending}
          onClick={() => onAction("done")}
        >
          Mark Done
        </button>
      </div>
    );
  }
  return null;
}

/** OL-083: Install offer — only when ≥2 active threads. */
function InstallOffer({ threadCount }: { threadCount: number }) {
  if (threadCount < 2) return null;
  return (
    <div class="border border-accent rounded-[2px] bg-[#EDF1FB] px-3 py-2.5 my-3">
      <p class="text-sm font-medium text-text-primary mb-1">
        You have {threadCount} active threads
      </p>
      <p class="text-xs text-text-muted mb-2">
        Install the OpenLnk app to manage all your commitments in one place.
      </p>
      <a
        href="https://openlnk.in/install"
        class="inline-block px-4 py-2 bg-accent text-white text-sm font-medium rounded-[4px] hover:bg-accent-hover no-underline"
      >
        Install OpenLnk
      </a>
    </div>
  );
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
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [threadCount, setThreadCount] = useState(0);
  const prevCommitment = useRef<Commitment | null>(null);

  // Extract token from URL path: /t/{token}
  const urlToken = window.location.pathname.split("/t/")[1] ?? "";
  const token = urlToken || getPersistedToken() || "";

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    persistSession(token);

    // OL-085: Track open/return funnel event
    const hasVisited = getPersistedToken() === token;
    trackFunnel(hasVisited ? "return" : "open");

    fetch(`${API_BASE}/threads/resolve/${encodeURIComponent(token)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.json();
      })
      .then(
        (data: {
          commitments: Commitment[];
          thread_count?: number;
        }) => {
          if (data.commitments.length > 0) {
            setCommitment(data.commitments[0]);
          }
          setThreadCount(data.thread_count ?? 0);
          setLoading(false);
        },
      )
      .catch(() => {
        setError("Link expired or invalid.");
        setLoading(false);
      });
  }, [token]);

  const handleAction = (newState: string) => {
    if (!commitment) return;
    prevCommitment.current = commitment;
    setCommitment({ ...commitment, state: newState });
    setActionError(null);
    setActionPending(true);

    fetch(`${API_BASE}/threads/resolve/${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: newState, version: commitment.version }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        setActionPending(false);
      })
      .catch(() => {
        // Revert on failure
        setCommitment(prevCommitment.current);
        setActionError("Action failed. Please try again.");
        setActionPending(false);
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
            <ActionButtons
              state={commitment.state}
              onAction={handleAction}
              pending={actionPending}
            />
            {actionError && (
              <p class="text-xs text-center" style={{ color: "#B91C1C" }}>
                {actionError}
              </p>
            )}
            {/* UPI payment button (OL-010, OL-103) */}
            {commitment.state === "accepted" &&
              (commitment.class === "fee" || commitment.class === "payment") &&
              commitment.amount_paise !== null && (
                <a
                  href={`upi://pay?am=${commitment.amount_paise / 100}&cu=${commitment.currency}&tn=${encodeURIComponent(commitment.title)}`}
                  class="block w-full py-2.5 bg-accent text-white text-sm font-semibold font-mono text-center rounded-[4px] hover:bg-accent-hover no-underline my-3"
                >
                  Pay {formatAmount(commitment.amount_paise, commitment.currency)} via UPI
                </a>
              )}
            <InstallOffer threadCount={threadCount} />
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
