/**
 * Daily brief page — AI-generated summary + commitments due today + at-risk.
 *
 * DESIGN.md: daily brief view (commitments + at-risk + conflicts).
 * Shows AI summary at top, then commitment groups by state priority.
 */

import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useQuery } from "@tanstack/react-query";
import { fetchCommitments, fetchBriefSummary } from "../api/client";
import CommitmentCard from "../components/CommitmentCard";
import { useAppStore } from "../store/app";
import { fonts } from "@openlnk/ui";

export default function DailyBriefPage() {
  const navigate = useNavigate();
  const { principalId } = useAppStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["commitments", principalId, "brief"],
    queryFn: () => fetchCommitments(principalId, { limit: 100 }),
  });

  const { data: briefData, isLoading: briefLoading } = useQuery({
    queryKey: ["brief-summary", principalId],
    queryFn: () => fetchBriefSummary(principalId),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const today = new Date().toDateString();
  const atRisk = data?.items.filter((c) => c.at_risk) ?? [];
  const dueToday =
    data?.items.filter(
      (c) => c.due_at && new Date(c.due_at).toDateString() === today,
    ) ?? [];
  const proposed =
    data?.items.filter((c) => c.state === "proposed") ?? [];

  return (
    <Box sx={{ maxWidth: 960, mx: "auto" }}>
      <Typography variant="h6" sx={{ mb: 0.5 }}>
        Daily Brief
      </Typography>
      <Typography
        sx={{
          fontFamily: fonts.mono,
          fontSize: 11,
          color: "text.secondary",
          mb: 3,
        }}
      >
        {new Date().toLocaleDateString("en-IN", {
          weekday: "long",
          day: "numeric",
          month: "long",
          year: "numeric",
        })}
      </Typography>

      {/* AI Summary */}
      {briefLoading && (
        <Box
          sx={{
            border: "1px solid #E8E4DD",
            p: 2,
            mb: 3,
            backgroundColor: "#FAFAF8",
          }}
        >
          <Typography sx={{ color: "text.secondary", fontSize: 13 }}>
            {"\u2014"} Generating summary...
          </Typography>
        </Box>
      )}
      {briefData && (
        <Box
          sx={{
            borderLeft: "3px solid #1A4FBF",
            pl: 2,
            pr: 2,
            py: 1.5,
            mb: 3,
            backgroundColor: "#FAFAF8",
          }}
        >
          <Typography
            sx={{
              fontFamily: fonts.mono,
              fontSize: 10,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#6B6456",
              mb: 0.5,
            }}
          >
            AI SUMMARY
          </Typography>
          <Typography
            sx={{
              fontSize: 14,
              lineHeight: 1.6,
              color: "#1A1814",
            }}
          >
            {briefData.summary}
          </Typography>
          {/* Stat row */}
          <Box
            sx={{
              display: "flex",
              gap: 3,
              mt: 1.5,
              pt: 1,
              borderTop: "1px solid #E8E4DD",
            }}
          >
            {[
              { label: "AT RISK", value: briefData.counts.at_risk, color: "#92600A" },
              { label: "DUE TODAY", value: briefData.counts.due_today, color: "#1A1814" },
              { label: "AWAITING", value: briefData.counts.proposed, color: "#1A1814" },
              { label: "DONE TODAY", value: briefData.counts.done_today, color: "#2E7D32" },
            ].map((stat) => (
              <Box key={stat.label}>
                <Typography
                  sx={{
                    fontFamily: fonts.mono,
                    fontSize: 18,
                    fontWeight: 600,
                    color: stat.color,
                  }}
                >
                  {stat.value}
                </Typography>
                <Typography
                  sx={{
                    fontFamily: fonts.mono,
                    fontSize: 9,
                    letterSpacing: "0.1em",
                    color: "#6B6456",
                  }}
                >
                  {stat.label}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      {isLoading && (
        <Typography sx={{ color: "text.secondary" }}>
          {"\u2014"} Loading brief...
        </Typography>
      )}

      {error && (
        <Typography sx={{ color: "error.main", fontSize: 12, mb: 2 }}>
          Failed to load daily brief.
        </Typography>
      )}

      {/* At-risk section */}
      {atRisk.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography
            sx={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#92600A",
              mb: 1,
            }}
          >
            At Risk ({atRisk.length})
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {atRisk.map((c) => (
              <CommitmentCard key={c.id} commitment={c} onClick={() => navigate(`/commitments/${c.id}`)} />
            ))}
          </Box>
        </Box>
      )}

      {/* Due today */}
      {dueToday.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography
            sx={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "text.secondary",
              mb: 1,
            }}
          >
            Due Today ({dueToday.length})
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {dueToday.map((c) => (
              <CommitmentCard key={c.id} commitment={c} onClick={() => navigate(`/commitments/${c.id}`)} />
            ))}
          </Box>
        </Box>
      )}

      {/* Pending proposals */}
      {proposed.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography
            sx={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "text.secondary",
              mb: 1,
            }}
          >
            Awaiting Action ({proposed.length})
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {proposed.map((c) => (
              <CommitmentCard key={c.id} commitment={c} onClick={() => navigate(`/commitments/${c.id}`)} />
            ))}
          </Box>
        </Box>
      )}

      {!isLoading &&
        atRisk.length === 0 &&
        dueToday.length === 0 &&
        proposed.length === 0 && (
          <Typography
            sx={{
              color: "text.secondary",
              fontWeight: 500,
              textAlign: "center",
              py: 6,
            }}
          >
            No commitments. Create one.
          </Typography>
        )}
    </Box>
  );
}
