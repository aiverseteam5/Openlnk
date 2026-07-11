/**
 * Create commitment page — manual entry form.
 *
 * Class-specific validation: fee/payment require amount (OL-009).
 * POST /commitments with Idempotency-Key (sacred rule #5).
 * Lifecycle stage: create.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "../store/app";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

const CLASSES = [
  { value: "fee", label: "Fee" },
  { value: "schedule", label: "Schedule" },
  { value: "task", label: "Task" },
  { value: "payment", label: "Payment" },
  { value: "custom", label: "Custom" },
];

export default function CreateCommitmentPage() {
  const navigate = useNavigate();
  const { principalId, selectedContextId } = useAppStore();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState("");
  const [commitmentClass, setCommitmentClass] = useState("task");
  const [amount, setAmount] = useState("");
  const [currency] = useState("INR");
  const [dueAt, setDueAt] = useState("");

  const requiresAmount = commitmentClass === "fee" || commitmentClass === "payment";

  const createMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        title,
        class: commitmentClass,
        currency,
        owner_id: principalId,
        context_id: selectedContextId ?? principalId,
      };
      if (amount) body.amount_paise = Math.round(parseFloat(amount) * 100);
      if (dueAt) body.due_at = new Date(dueAt).toISOString();

      const res = await fetch(`${API_BASE}/commitments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Principal-Id": principalId,
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API ${res.status}: ${text}`);
      }
      return res.json();
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["commitments"] });
      navigate("/commitments");
    },
  });

  const valid =
    title.trim().length > 0 &&
    (!requiresAmount || (amount && parseFloat(amount) > 0));

  return (
    <Box sx={{ maxWidth: 640, mx: "auto" }}>
      <Button
        variant="text"
        size="small"
        onClick={() => navigate(-1)}
        sx={{ mb: 1, color: "text.secondary", textTransform: "none" }}
      >
        &larr; Back
      </Button>

      <Typography variant="h6" sx={{ mb: 2 }}>
        Create Commitment
      </Typography>

      <Box
        sx={{
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "2px",
          bgcolor: "background.paper",
          p: 2,
        }}
      >
        <TextField
          label="Title"
          fullWidth
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          sx={{ mb: 2 }}
          slotProps={{ htmlInput: { maxLength: 500 } }}
        />

        <TextField
          label="Class"
          fullWidth
          select
          value={commitmentClass}
          onChange={(e) => setCommitmentClass(e.target.value)}
          sx={{ mb: 2 }}
        >
          {CLASSES.map((c) => (
            <MenuItem key={c.value} value={c.value}>
              {c.label}
            </MenuItem>
          ))}
        </TextField>

        <TextField
          label={`Amount (${currency})${requiresAmount ? " *" : ""}`}
          fullWidth
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          error={requiresAmount && amount !== "" && parseFloat(amount) <= 0}
          helperText={
            requiresAmount && !amount
              ? "Required for fee/payment commitments"
              : undefined
          }
          sx={{ mb: 2 }}
        />

        <TextField
          label="Due date"
          fullWidth
          type="datetime-local"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
          sx={{ mb: 2 }}
        />

        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="contained"
            fullWidth
            disabled={!valid || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            Create
          </Button>
          <Button
            variant="outlined"
            fullWidth
            onClick={() => navigate(-1)}
          >
            Cancel
          </Button>
        </Box>

        {createMutation.isError && (
          <Typography sx={{ color: "error.main", fontSize: 12, mt: 1 }}>
            Failed to create commitment.
          </Typography>
        )}
      </Box>
    </Box>
  );
}
