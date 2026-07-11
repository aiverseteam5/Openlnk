/**
 * Daily brief page — commitments due today + at-risk summary.
 *
 * DESIGN.md: daily brief view (commitments + at-risk + conflicts).
 * Shows today's commitments grouped by state priority.
 */

import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useQuery } from "@tanstack/react-query";
import { fetchCommitments } from "../api/client";
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
