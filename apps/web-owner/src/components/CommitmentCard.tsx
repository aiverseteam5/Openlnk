/**
 * CommitmentCard — per DESIGN.md commitment card anatomy.
 *
 * [3px STATE BAR] | [ID mono muted]        [STATE BADGE mono]
 *                 | [TITLE DM Sans 600]
 *                 | [Counterparty/Class]    [AMOUNT mono]
 *                 | [Provenance]            [DUE DATE mono]
 *
 * No shadows, no icons replacing state labels, no nested tappable elements.
 */

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { stateColors, fonts, type CommitmentState } from "@openlnk/ui";
import type { Commitment } from "../api/client";

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

function shortId(id: string): string {
  return `CMT-${id.slice(0, 4).toUpperCase()}`;
}

interface CommitmentCardProps {
  commitment: Commitment;
  onClick?: () => void;
}

export default function CommitmentCard({
  commitment,
  onClick,
}: CommitmentCardProps) {
  const stateKey = (
    commitment.at_risk ? "overdue" : commitment.state
  ) as CommitmentState;
  const sc = stateColors[stateKey] ?? stateColors.proposed;

  return (
    <Box
      onClick={onClick}
      sx={{
        display: "flex",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "2px",
        bgcolor: "background.paper",
        cursor: onClick ? "pointer" : "default",
        "&:hover": onClick
          ? { borderColor: "primary.main", bgcolor: "#FAFAF8" }
          : {},
        overflow: "hidden",
      }}
    >
      {/* 3px state bar */}
      <Box sx={{ width: 3, flexShrink: 0, bgcolor: sc.leftBar }} />

      {/* Card content */}
      <Box sx={{ flex: 1, px: 1.5, py: 1.25 }}>
        {/* Row 1: ID + State badge */}
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
              color: "text.secondary",
            }}
          >
            {shortId(commitment.id)}
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

        {/* Row 2: Title */}
        <Typography
          sx={{
            fontSize: 14,
            fontWeight: 600,
            lineHeight: "20px",
            mb: 0.5,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {commitment.title}
        </Typography>

        {/* Row 3: Counterparty · Class + Amount */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography
            sx={{ fontSize: 12, color: "text.secondary" }}
          >
            {commitment.counterparty_id
              ? `${commitment.counterparty_id.slice(0, 8)} \u00B7 ${commitment.class}`
              : commitment.class}
          </Typography>
          {commitment.amount_paise !== null && (
            <Typography
              sx={{
                fontFamily: fonts.mono,
                fontSize: 15,
                fontWeight: 600,
                lineHeight: "20px",
              }}
            >
              {formatAmount(commitment.amount_paise, commitment.currency)}
            </Typography>
          )}
        </Box>

        {/* Row 4: Provenance + Due date */}
        {(commitment.provenance_kind || commitment.due_at) && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mt: 0.5,
            }}
          >
            <Typography
              sx={{ fontSize: 11, color: "text.secondary" }}
            >
              {commitment.provenance_kind ?? ""}
            </Typography>
            {commitment.due_at && (
              <Typography
                sx={{
                  fontFamily: fonts.mono,
                  fontSize: 11,
                  color: "text.secondary",
                }}
              >
                {formatDue(commitment.due_at)}
              </Typography>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
}
