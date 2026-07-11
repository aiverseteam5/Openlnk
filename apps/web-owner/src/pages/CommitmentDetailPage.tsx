/**
 * Commitment detail page — full data, state transitions, corrections, audit trail.
 *
 * DESIGN.md: Bottom-sheet style on mobile, full page on desktop.
 * State changes are inline timestamped audit entries, not toasts.
 * Corrections in ≤2 taps (OL-026).
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchCommitment,
  transitionState,
} from "../api/client";
import { useAppStore } from "../store/app";
import { stateColors, fonts, type CommitmentState } from "@openlnk/ui";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

// Valid transitions per current state
const TRANSITIONS: Record<string, { label: string; target: string }[]> = {
  proposed: [
    { label: "Accept", target: "accepted" },
    { label: "Reject", target: "cancelled" },
  ],
  accepted: [{ label: "Mark In Progress", target: "in_progress" }],
  in_progress: [
    { label: "Mark Done", target: "done" },
    { label: "Mark Broken", target: "broken" },
  ],
};

function formatAmount(paise: number | null, currency: string): string {
  if (paise === null) return "\u2014";
  const amount = paise / 100;
  if (currency === "INR") return `\u20B9${amount.toLocaleString("en-IN")}`;
  return `${currency} ${amount.toFixed(2)}`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "\u2014";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DataRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between", py: 0.75 }}>
      <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
        {label}
      </Typography>
      <Typography
        sx={{
          fontSize: 14,
          fontWeight: 600,
          fontFamily: mono ? fonts.mono : undefined,
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

export default function CommitmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { principalId } = useAppStore();
  const queryClient = useQueryClient();

  const [correctionMode, setCorrectionMode] = useState<"edit" | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editAmount, setEditAmount] = useState("");

  const { data: commitment, isLoading } = useQuery({
    queryKey: ["commitment", id],
    queryFn: () => fetchCommitment(principalId, id!),
    enabled: !!id,
  });

  const transitionMutation = useMutation({
    mutationFn: ({
      newState,
      version,
    }: {
      newState: string;
      version: number;
    }) => transitionState(principalId, id!, newState, version),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["commitment", id] });
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
    },
  });

  const correctMutation = useMutation({
    mutationFn: async (body: { action: string; edits?: Record<string, unknown> }) => {
      const res = await fetch(`${API_BASE}/commitments/${id}/correct`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Principal-Id": principalId,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      setCorrectionMode(null);
      void queryClient.invalidateQueries({ queryKey: ["commitment", id] });
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
    },
  });

  if (isLoading || !commitment) {
    return (
      <Box sx={{ maxWidth: 640, mx: "auto", py: 6 }}>
        <Typography sx={{ color: "text.secondary", textAlign: "center" }}>
          {"\u2014"} Loading...
        </Typography>
      </Box>
    );
  }

  const stateKey = (
    commitment.at_risk ? "overdue" : commitment.state
  ) as CommitmentState;
  const sc = stateColors[stateKey] ?? stateColors.proposed;
  const transitions = TRANSITIONS[commitment.state] ?? [];

  return (
    <Box sx={{ maxWidth: 640, mx: "auto" }}>
      {/* Back link */}
      <Button
        variant="text"
        size="small"
        onClick={() => navigate(-1)}
        sx={{ mb: 1, color: "text.secondary", textTransform: "none" }}
      >
        &larr; Back
      </Button>

      {/* Header card */}
      <Box
        sx={{
          display: "flex",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "2px",
          bgcolor: "background.paper",
          overflow: "hidden",
          mb: 2,
        }}
      >
        <Box sx={{ width: 3, flexShrink: 0, bgcolor: sc.leftBar }} />
        <Box sx={{ flex: 1, px: 2, py: 2 }}>
          {/* ID + Badge */}
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
            <Typography
              sx={{ fontFamily: fonts.mono, fontSize: 11, color: "text.secondary" }}
            >
              CMT-{commitment.id.slice(0, 4).toUpperCase()}
            </Typography>
            <Box
              sx={{
                fontFamily: fonts.mono,
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: "0.1em",
                color: sc.text,
                bgcolor: sc.background,
                px: 1,
                py: 0.25,
                borderRadius: "9999px",
              }}
            >
              {sc.label}
            </Box>
          </Box>

          {/* Title */}
          <Typography variant="h5" sx={{ mb: 1.5 }}>
            {commitment.title}
          </Typography>

          {/* Data rows */}
          <DataRow label="Class" value={commitment.class} />
          <DataRow
            label="Amount"
            value={formatAmount(commitment.amount_paise, commitment.currency)}
            mono
          />
          <DataRow label="Due" value={formatDate(commitment.due_at)} mono />
          <DataRow label="Created" value={formatDate(commitment.created_at)} mono />
          <DataRow label="Version" value={String(commitment.version)} mono />
          {commitment.provenance_kind && (
            <DataRow label="Provenance" value={commitment.provenance_kind} />
          )}
          {commitment.extraction_confidence !== null && (
            <DataRow
              label="Extraction confidence"
              value={`${(commitment.extraction_confidence * 100).toFixed(0)}%`}
              mono
            />
          )}
        </Box>
      </Box>

      {/* State transition buttons */}
      {transitions.length > 0 && (
        <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
          {transitions.map((t) => (
            <Button
              key={t.target}
              variant={t.target === "cancelled" || t.target === "broken" ? "outlined" : "contained"}
              fullWidth
              disabled={transitionMutation.isPending}
              onClick={() =>
                transitionMutation.mutate({
                  newState: t.target,
                  version: commitment.version,
                })
              }
            >
              {t.label}
            </Button>
          ))}
        </Box>
      )}

      {transitionMutation.isError && (
        <Typography sx={{ color: "error.main", fontSize: 12, mb: 2 }}>
          Transition failed. The commitment may have been updated.
        </Typography>
      )}

      {/* UPI payment button (OL-010, OL-103) — fee/payment after accepted */}
      {commitment.state === "accepted" &&
        (commitment.class === "fee" || commitment.class === "payment") &&
        commitment.amount_paise !== null && (
          <Button
            variant="contained"
            fullWidth
            href={`upi://pay?pa=&pn=OpenLnk&am=${commitment.amount_paise / 100}&cu=${commitment.currency}&tn=${encodeURIComponent(commitment.title)}`}
            sx={{ mb: 2, fontFamily: fonts.mono, fontWeight: 600 }}
          >
            Pay {formatAmount(commitment.amount_paise, commitment.currency)} via UPI
          </Button>
        )}

      <Divider sx={{ my: 2 }} />

      {/* Corrections (OL-026) — ≤2 taps */}
      {commitment.state === "proposed" && commitment.provenance_kind && (
        <Box sx={{ mb: 2 }}>
          <Typography
            sx={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.08em",
              color: "text.secondary",
              mb: 1,
            }}
          >
            EXTRACTION CORRECTION
          </Typography>

          {correctionMode === null ? (
            <Box sx={{ display: "flex", gap: 1 }}>
              {/* Tap 1: choose reject or edit */}
              <Button
                variant="outlined"
                size="small"
                color="error"
                onClick={() =>
                  correctMutation.mutate({ action: "reject" })
                }
                disabled={correctMutation.isPending}
              >
                Reject extraction
              </Button>
              <Button
                variant="outlined"
                size="small"
                onClick={() => {
                  setEditTitle(commitment.title);
                  setEditAmount(
                    commitment.amount_paise !== null
                      ? String(commitment.amount_paise / 100)
                      : "",
                  );
                  setCorrectionMode("edit");
                }}
              >
                Edit &amp; correct
              </Button>
            </Box>
          ) : (
            /* Tap 2: submit edits */
            <Box>
              <TextField
                label="Title"
                fullWidth
                size="small"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                sx={{ mb: 1 }}
              />
              <TextField
                label="Amount"
                fullWidth
                size="small"
                type="number"
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
                sx={{ mb: 1 }}
              />
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  variant="contained"
                  size="small"
                  disabled={correctMutation.isPending}
                  onClick={() => {
                    const edits: Record<string, unknown> = {};
                    if (editTitle !== commitment.title) edits.title = editTitle;
                    if (editAmount) {
                      const paise = Math.round(parseFloat(editAmount) * 100);
                      if (paise !== commitment.amount_paise)
                        edits.amount_paise = paise;
                    }
                    correctMutation.mutate({ action: "edit", edits });
                  }}
                >
                  Submit correction
                </Button>
                <Button
                  variant="text"
                  size="small"
                  onClick={() => setCorrectionMode(null)}
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          )}

          {correctMutation.isError && (
            <Typography sx={{ color: "error.main", fontSize: 12, mt: 1 }}>
              Correction failed.
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
}
