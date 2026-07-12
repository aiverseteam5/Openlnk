/**
 * Business console — dashboard, roster, fee cycles (OL-100..105).
 *
 * Tabbed view: Dashboard | Roster | Fee Cycles
 * DESIGN.md: DM Sans + JetBrains Mono, #F5F2EC bg, no shadows.
 */

import { useState, useRef } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "../store/app";
import { fonts } from "@openlnk/ui";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

// ── API helpers ──

async function apiFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("openlnk_access_token");
  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((opts.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

interface Business {
  id: string;
  name: string;
  vertical: string;
  upi_vpa: string | null;
  whatsapp_number: string | null;
  subscription_state: string;
}

interface Dashboard {
  business: Business;
  counts: {
    pending: number;
    at_risk: number;
    done: number;
    total: number;
    students: number;
  };
  roi: {
    fees_recovered_paise: number;
    subscription_cost_paise: number;
    period: string;
  };
}

interface StagingRecord {
  id: number;
  student_name: string;
  parent_phone: string;
  batch: string | null;
  consent_received: boolean;
}

interface RosterImportResult {
  imported: number;
  errors: string[];
  records: StagingRecord[];
}

type Tab = "dashboard" | "roster" | "fees";

// ── Stat Card ──

function StatCard({ label, value, mono }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "2px",
        bgcolor: "background.paper",
        px: 2,
        py: 1.5,
        flex: 1,
        minWidth: 120,
      }}
    >
      <Typography sx={{ fontSize: 11, color: "text.secondary", mb: 0.5 }}>
        {label}
      </Typography>
      <Typography
        sx={{
          fontFamily: mono ? fonts.mono : undefined,
          fontSize: 20,
          fontWeight: 600,
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

// ── Dashboard Tab ──

function DashboardTab({ businessId }: { businessId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", businessId],
    queryFn: () => apiFetch<Dashboard>(`/businesses/${businessId}/dashboard`),
  });

  if (isLoading || !data) {
    return <Typography sx={{ color: "text.secondary" }}>{"\u2014"} Loading dashboard...</Typography>;
  }

  const { counts, roi } = data;
  const recovered = roi.fees_recovered_paise / 100;
  const cost = roi.subscription_cost_paise / 100;

  return (
    <Box>
      {/* Stats row */}
      <Box sx={{ display: "flex", gap: 1.5, mb: 3, flexWrap: "wrap" }}>
        <StatCard label="Students" value={counts.students} mono />
        <StatCard label="Pending" value={counts.pending} mono />
        <StatCard label="At Risk" value={counts.at_risk} mono />
        <StatCard label="Done" value={counts.done} mono />
        <StatCard label="Total" value={counts.total} mono />
      </Box>

      {/* ROI section (OL-105) */}
      <Box
        sx={{
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "2px",
          bgcolor: "background.paper",
          px: 2,
          py: 1.5,
          mb: 2,
        }}
      >
        <Typography
          sx={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.08em",
            color: "text.secondary",
            mb: 1,
          }}
        >
          ROI — {roi.period.replace("_", " ").toUpperCase()}
        </Typography>
        <Box sx={{ display: "flex", gap: 3 }}>
          <Box>
            <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Fees recovered</Typography>
            <Typography sx={{ fontFamily: fonts.mono, fontSize: 16, fontWeight: 600 }}>
              {"\u20B9"}{recovered.toLocaleString("en-IN")}
            </Typography>
          </Box>
          <Box>
            <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Subscription cost</Typography>
            <Typography sx={{ fontFamily: fonts.mono, fontSize: 16, fontWeight: 600 }}>
              {"\u20B9"}{cost.toLocaleString("en-IN")}
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Business details */}
      <Box
        sx={{
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "2px",
          bgcolor: "background.paper",
          px: 2,
          py: 1.5,
        }}
      >
        <Typography sx={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", color: "text.secondary", mb: 1 }}>
          CENTER DETAILS
        </Typography>
        <Typography sx={{ fontSize: 14, fontWeight: 600 }}>{data.business.name}</Typography>
        <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
          {data.business.vertical} &middot; {data.business.subscription_state}
        </Typography>
        {data.business.upi_vpa && (
          <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, mt: 0.5 }}>
            UPI: {data.business.upi_vpa}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

// ── Roster Tab ──

function RosterTab({ businessId }: { businessId: string }) {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: records, isLoading } = useQuery({
    queryKey: ["roster", businessId],
    queryFn: () => apiFetch<StagingRecord[]>(`/businesses/${businessId}/roster`),
  });

  const importMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const token = localStorage.getItem("openlnk_access_token");
      const res = await fetch(`${API_BASE}/businesses/${businessId}/roster/import`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: formData,
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return res.json() as Promise<RosterImportResult>;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["roster", businessId] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", businessId] });
    },
  });

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography sx={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", color: "text.secondary" }}>
          STUDENT ROSTER ({records?.length ?? 0})
        </Typography>
        <Box>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) importMutation.mutate(f);
            }}
          />
          <Button
            variant="contained"
            size="small"
            disabled={importMutation.isPending}
            onClick={() => fileRef.current?.click()}
          >
            {importMutation.isPending ? "Importing..." : "Import CSV"}
          </Button>
        </Box>
      </Box>

      {importMutation.isError && (
        <Typography sx={{ color: "error.main", fontSize: 12, mb: 1 }}>
          Import failed.
        </Typography>
      )}

      {importMutation.isSuccess && importMutation.data && (
        <Box sx={{ mb: 2, p: 1.5, bgcolor: "#F0FFF4", border: "1px solid #C6F6D5", borderRadius: "2px" }}>
          <Typography sx={{ fontSize: 12 }}>
            Imported {importMutation.data.imported} students.
            {importMutation.data.errors.length > 0 && ` ${importMutation.data.errors.length} errors.`}
          </Typography>
        </Box>
      )}

      {isLoading && <Typography sx={{ color: "text.secondary" }}>{"\u2014"} Loading...</Typography>}

      {records && records.length === 0 && (
        <Typography sx={{ color: "text.secondary", textAlign: "center", py: 4, fontSize: 14 }}>
          No students imported yet. Upload a CSV with columns: student_name, parent_phone, batch
        </Typography>
      )}

      {records && records.length > 0 && (
        <Box
          component="table"
          sx={{
            width: "100%",
            borderCollapse: "collapse",
            "& th, & td": {
              textAlign: "left",
              px: 1.5,
              py: 0.75,
              borderBottom: "1px solid",
              borderColor: "divider",
              fontSize: 13,
            },
            "& th": {
              fontFamily: fonts.mono,
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.05em",
              color: "text.secondary",
            },
          }}
        >
          <thead>
            <tr>
              <th>Student</th>
              <th>Phone</th>
              <th>Batch</th>
              <th>Consent</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id}>
                <td>{r.student_name}</td>
                <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>{r.parent_phone}</td>
                <td>{r.batch ?? "\u2014"}</td>
                <td>
                  <Typography
                    sx={{
                      fontFamily: fonts.mono,
                      fontSize: 11,
                      fontWeight: 600,
                      color: r.consent_received ? "#2E7D32" : "#92600A",
                    }}
                  >
                    {r.consent_received ? "YES" : "PENDING"}
                  </Typography>
                </td>
              </tr>
            ))}
          </tbody>
        </Box>
      )}
    </Box>
  );
}

// ── Fee Cycles Tab ──

function FeeCyclesTab({ businessId }: { businessId: string }) {
  const queryClient = useQueryClient();
  const [cycleLabel, setCycleLabel] = useState("");
  const [amount, setAmount] = useState("");
  const [batch, setBatch] = useState("");

  const generateMutation = useMutation({
    mutationFn: async () => {
      return apiFetch<{ generated: number; cycle_label: string }>(
        `/businesses/${businessId}/fee-cycles`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": crypto.randomUUID(),
          },
          body: JSON.stringify({
            cycle_label: cycleLabel,
            amount_paise: Math.round(parseFloat(amount) * 100),
            batch: batch || null,
          }),
        },
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard", businessId] });
      setCycleLabel("");
      setAmount("");
      setBatch("");
    },
  });

  return (
    <Box>
      <Typography
        sx={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", color: "text.secondary", mb: 2 }}
      >
        GENERATE FEE CYCLE
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
          fullWidth
          size="small"
          label="Cycle label"
          placeholder="July 2026"
          value={cycleLabel}
          onChange={(e) => setCycleLabel(e.target.value)}
          sx={{ mb: 1.5 }}
        />
        <TextField
          fullWidth
          size="small"
          label="Amount (₹)"
          type="number"
          placeholder="5000"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          sx={{ mb: 1.5 }}
        />
        <TextField
          fullWidth
          size="small"
          label="Batch (optional)"
          placeholder="All batches if empty"
          value={batch}
          onChange={(e) => setBatch(e.target.value)}
          sx={{ mb: 2 }}
        />
        <Button
          variant="contained"
          fullWidth
          disabled={generateMutation.isPending || !cycleLabel || !amount}
          onClick={() => generateMutation.mutate()}
        >
          {generateMutation.isPending ? "Generating..." : "Generate Fee Commitments"}
        </Button>

        {generateMutation.isSuccess && generateMutation.data && (
          <Typography sx={{ color: "#2E7D32", fontSize: 12, mt: 1 }}>
            Generated {generateMutation.data.generated} fee commitments for {generateMutation.data.cycle_label}.
          </Typography>
        )}

        {generateMutation.isError && (
          <Typography sx={{ color: "error.main", fontSize: 12, mt: 1 }}>
            Failed to generate fee cycle. Ensure students have consent.
          </Typography>
        )}
      </Box>
    </Box>
  );
}

// ── Main Console Page ──

const TABS: { key: Tab; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "roster", label: "Roster" },
  { key: "fees", label: "Fee Cycles" },
];

export default function ConsolePage() {
  useAppStore(); // ensure auth state is available
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [selectedBusiness] = useState<string | null>(null);

  const { data: businesses, isLoading } = useQuery({
    queryKey: ["businesses"],
    queryFn: () => apiFetch<Business[]>("/businesses"),
  });

  // Auto-select first business
  const businessId = selectedBusiness ?? businesses?.[0]?.id ?? null;

  return (
    <Box sx={{ maxWidth: 960, mx: "auto" }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Business Console
      </Typography>

      {isLoading && (
        <Typography sx={{ color: "text.secondary" }}>{"\u2014"} Loading...</Typography>
      )}

      {businesses && businesses.length === 0 && (
        <Typography sx={{ color: "text.secondary", textAlign: "center", py: 6 }}>
          No businesses linked to your account.
        </Typography>
      )}

      {businessId && (
        <>
          {/* Tab bar */}
          <Box sx={{ display: "flex", gap: 0, mb: 2 }}>
            {TABS.map((tab) => (
              <Box
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                sx={{
                  px: 2,
                  py: 0.75,
                  cursor: "pointer",
                  fontFamily: fonts.mono,
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: "0.08em",
                  borderBottom: "2px solid",
                  borderColor: activeTab === tab.key ? "primary.main" : "transparent",
                  color: activeTab === tab.key ? "primary.main" : "text.secondary",
                  "&:hover": { color: "primary.main" },
                }}
              >
                {tab.label.toUpperCase()}
              </Box>
            ))}
          </Box>

          <Divider sx={{ mb: 2 }} />

          {activeTab === "dashboard" && <DashboardTab businessId={businessId} />}
          {activeTab === "roster" && <RosterTab businessId={businessId} />}
          {activeTab === "fees" && <FeeCyclesTab businessId={businessId} />}
        </>
      )}
    </Box>
  );
}
