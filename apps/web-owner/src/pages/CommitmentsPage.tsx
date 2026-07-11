/**
 * Commitment ledger page — cursor-paginated list with state filter.
 *
 * DESIGN.md: unified ledger view, max-content 960px.
 * CLAUDE.md: cursor pagination only.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { useQuery } from "@tanstack/react-query";
import { fetchCommitments } from "../api/client";
import CommitmentCard from "../components/CommitmentCard";
import StateFilter from "../components/StateFilter";
import { useAppStore } from "../store/app";

export default function CommitmentsPage() {
  const navigate = useNavigate();
  const { principalId, selectedContextId, stateFilter, setStateFilter } =
    useAppStore();
  const [cursor, setCursor] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["commitments", principalId, selectedContextId, stateFilter, cursor],
    queryFn: () =>
      fetchCommitments(principalId, {
        context_id: selectedContextId ?? undefined,
        state: stateFilter ?? undefined,
        cursor: cursor ?? undefined,
        limit: 50,
      }),
  });

  return (
    <Box sx={{ maxWidth: 960, mx: "auto" }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h6">
          Commitments
        </Typography>
        <Button
          variant="contained"
          size="small"
          onClick={() => navigate("/commitments/new")}
        >
          Create
        </Button>
      </Box>

      <StateFilter selected={stateFilter} onChange={setStateFilter} />

      {isLoading && (
        <Typography sx={{ color: "text.secondary" }}>
          {"\u2014"} Loading...
        </Typography>
      )}

      {error && (
        <Typography sx={{ color: "error.main" }}>
          Failed to load commitments.
        </Typography>
      )}

      {data && data.items.length === 0 && !isLoading && (
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

      {data && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {data.items.map((c) => (
            <CommitmentCard
              key={c.id}
              commitment={c}
              onClick={() => navigate(`/commitments/${c.id}`)}
            />
          ))}
        </Box>
      )}

      {data?.has_more && (
        <Box sx={{ mt: 2, textAlign: "center" }}>
          <Button
            variant="outlined"
            size="small"
            onClick={() => setCursor(data.next_cursor)}
          >
            Load more
          </Button>
        </Box>
      )}
    </Box>
  );
}
