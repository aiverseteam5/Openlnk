/**
 * Extraction inbox — AI-extracted commitments awaiting review.
 *
 * Shows only proposed commitments with provenance_kind set (extracted,
 * not manually created). Prominently displays confidence score and
 * provides inline accept/reject actions (OL-020, OL-021, OL-022, OL-026).
 *
 * DESIGN.md: state bar, mono confidence, 2-tap correction flow.
 */

import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchCommitments, transitionState } from "../api/client";
import type { Commitment } from "../api/client";
import { useAppStore } from "../store/app";
import { stateColors, fonts } from "@openlnk/ui";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

function formatAmount(paise: number | null, currency: string): string {
  if (paise === null) return "";
  const amount = paise / 100;
  if (currency === "INR") return `\u20B9${amount.toLocaleString("en-IN")}`;
  return `${currency} ${amount.toFixed(2)}`;
}

function formatDue(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.95) return "#2E7D32"; // high
  if (confidence >= 0.85) return "#92600A"; // medium
  return "#C62828"; // low
}

function ExtractionCard({
  commitment,
  onAccept,
  onReject,
  isPending,
}: {
  commitment: Commitment;
  onAccept: () => void;
  onReject: () => void;
  isPending: boolean;
}) {
  const navigate = useNavigate();
  const sc = stateColors.proposed;
  const confidence = commitment.extraction_confidence ?? 0;

  return (
    <Box
      sx={{
        display: "flex",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "2px",
        bgcolor: "background.paper",
        overflow: "hidden",
      }}
    >
      {/* 3px state bar */}
      <Box sx={{ width: 3, flexShrink: 0, bgcolor: sc.leftBar }} />

      <Box sx={{ flex: 1, px: 1.5, py: 1.25 }}>
        {/* Row 1: Provenance + Confidence */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 0.5,
          }}
        >
          <Typography
            sx={{
              fontFamily: fonts.mono,
              fontSize: 10,
              letterSpacing: "0.08em",
              color: "text.secondary",
              textTransform: "uppercase",
            }}
          >
            {commitment.provenance_kind}
          </Typography>
          <Typography
            sx={{
              fontFamily: fonts.mono,
              fontSize: 11,
              fontWeight: 600,
              color: confidenceColor(confidence),
            }}
          >
            {(confidence * 100).toFixed(0)}% confidence
          </Typography>
        </Box>

        {/* Row 2: Title (clickable to detail) */}
        <Typography
          onClick={() => navigate(`/commitments/${commitment.id}`)}
          sx={{
            fontSize: 14,
            fontWeight: 600,
            lineHeight: "20px",
            mb: 0.5,
            cursor: "pointer",
            "&:hover": { color: "primary.main" },
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {commitment.title}
        </Typography>

        {/* Row 3: Class + Amount */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 0.75,
          }}
        >
          <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
            {commitment.class}
          </Typography>
          <Box sx={{ display: "flex", gap: 2 }}>
            {commitment.amount_paise !== null && (
              <Typography
                sx={{
                  fontFamily: fonts.mono,
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                {formatAmount(commitment.amount_paise, commitment.currency)}
              </Typography>
            )}
            {commitment.due_at && (
              <Typography
                sx={{
                  fontFamily: fonts.mono,
                  fontSize: 11,
                  color: "text.secondary",
                  alignSelf: "center",
                }}
              >
                {formatDue(commitment.due_at)}
              </Typography>
            )}
          </Box>
        </Box>

        {/* Action buttons: Accept / Reject / Edit */}
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="contained"
            size="small"
            disabled={isPending}
            onClick={onAccept}
            sx={{ flex: 1 }}
          >
            Accept
          </Button>
          <Button
            variant="outlined"
            size="small"
            color="error"
            disabled={isPending}
            onClick={onReject}
            sx={{ flex: 1 }}
          >
            Reject
          </Button>
          <Button
            variant="outlined"
            size="small"
            disabled={isPending}
            onClick={() => navigate(`/commitments/${commitment.id}`)}
          >
            Edit
          </Button>
        </Box>
      </Box>
    </Box>
  );
}

export default function ExtractionInboxPage() {
  const { principalId, selectedContextId } = useAppStore();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["commitments", principalId, selectedContextId, "proposed", "inbox"],
    queryFn: () =>
      fetchCommitments(principalId, {
        context_id: selectedContextId ?? undefined,
        state: "proposed",
        limit: 100,
      }),
  });

  // Filter to only extracted commitments (provenance_kind is set)
  const extracted =
    data?.items.filter((c) => c.provenance_kind !== null) ?? [];

  const acceptMutation = useMutation({
    mutationFn: ({ id, version }: { id: string; version: number }) =>
      transitionState(principalId, id, "accepted", version),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${API_BASE}/commitments/${id}/correct`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Principal-Id": principalId,
        },
        body: JSON.stringify({ action: "reject" }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
    },
  });

  const isPending = acceptMutation.isPending || rejectMutation.isPending;

  return (
    <Box sx={{ maxWidth: 960, mx: "auto" }}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6">
          Extraction Inbox
        </Typography>
        <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
          AI-extracted commitments awaiting your review
        </Typography>
      </Box>

      {isLoading && (
        <Typography sx={{ color: "text.secondary" }}>
          {"\u2014"} Loading...
        </Typography>
      )}

      {error && (
        <Typography sx={{ color: "error.main", fontSize: 12 }}>
          Failed to load extraction inbox.
        </Typography>
      )}

      {(acceptMutation.isError || rejectMutation.isError) && (
        <Typography sx={{ color: "error.main", fontSize: 12, mb: 1 }}>
          Action failed. The commitment may have been updated.
        </Typography>
      )}

      {extracted.length === 0 && !isLoading && (
        <Typography
          sx={{
            color: "text.secondary",
            fontWeight: 500,
            textAlign: "center",
            py: 6,
          }}
        >
          No pending extractions.
        </Typography>
      )}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {extracted.map((c) => (
          <ExtractionCard
            key={c.id}
            commitment={c}
            isPending={isPending}
            onAccept={() =>
              acceptMutation.mutate({ id: c.id, version: c.version })
            }
            onReject={() => rejectMutation.mutate(c.id)}
          />
        ))}
      </Box>
    </Box>
  );
}
