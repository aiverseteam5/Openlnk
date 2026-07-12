/**
 * Web-owner app — React + MUI center console.
 *
 * DESIGN.md: #F5F2EC background, max-content 960px, DM Sans + JetBrains Mono.
 * No dark mode, no avatars, no skeleton loaders.
 */

import { useState, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { ThemeProvider, CssBaseline } from "@mui/material";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import theme from "./theme/theme";
import { useContextSync } from "./hooks/useContextSync";
import { useAppStore } from "./store/app";
import { fetchContexts } from "./api/client";
import { fonts } from "@openlnk/ui";

const DailyBriefPage = lazy(() => import("./pages/DailyBriefPage"));
const CommitmentsPage = lazy(() => import("./pages/CommitmentsPage"));
const CreateCommitmentPage = lazy(() => import("./pages/CreateCommitmentPage"));
const CommitmentDetailPage = lazy(() => import("./pages/CommitmentDetailPage"));
const ExtractionInboxPage = lazy(() => import("./pages/ExtractionInboxPage"));
const ConsolePage = lazy(() => import("./pages/ConsolePage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

const NAV_ITEMS = [
  { label: "Daily Brief", path: "/" },
  { label: "Inbox", path: "/inbox" },
  { label: "Commitments", path: "/commitments" },
  { label: "Console", path: "/console" },
];

/** Context selector (OL-043): switch between household/business contexts. */
function ContextSelector() {
  const { principalId, selectedContextId, setSelectedContextId } = useAppStore();
  const { data: contexts } = useQuery({
    queryKey: ["contexts", principalId],
    queryFn: () => fetchContexts(principalId),
  });

  if (!contexts || contexts.length <= 1) return null;

  return (
    <Box sx={{ px: 2, mb: 2 }}>
      <Typography
        sx={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          color: "text.secondary",
          mb: 0.5,
        }}
      >
        CONTEXT
      </Typography>
      <Select
        size="small"
        fullWidth
        value={selectedContextId ?? "all"}
        onChange={(e) =>
          setSelectedContextId(e.target.value === "all" ? null : e.target.value)
        }
        sx={{ fontSize: 13 }}
      >
        <MenuItem value="all">All contexts</MenuItem>
        {contexts.map((ctx) => (
          <MenuItem key={ctx.id} value={ctx.id}>
            {ctx.label || ctx.kind}
          </MenuItem>
        ))}
      </Select>
    </Box>
  );
}

function Sidebar() {
  const { logout } = useAppStore();

  return (
    <Box
      sx={{
        width: 220,
        flexShrink: 0,
        bgcolor: "#FAFAF8",
        borderRight: "1px solid",
        borderColor: "divider",
        py: 2,
        display: { xs: "none", md: "block" },
        justifyContent: "space-between",
        flexDirection: "column",
      }}
    >
      <Box>
        <Typography
          sx={{
            fontFamily: fonts.mono,
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "0.08em",
            color: "primary.main",
            px: 2,
            mb: 2,
          }}
        >
          OPENLNK
        </Typography>
        <List disablePadding>
          {NAV_ITEMS.map((item) => (
            <ListItemButton
              key={item.path}
              component={NavLink}
              to={item.path}
              sx={{
                px: 2,
                py: 0.75,
                "&.active": {
                  bgcolor: "primary.main",
                  color: "primary.contrastText",
                  "& .MuiListItemText-primary": {
                    color: "primary.contrastText",
                  },
                },
              }}
            >
              <ListItemText
                primary={item.label}
                slotProps={{ primary: { sx: { fontSize: 14, fontWeight: 500 } } }}
              />
            </ListItemButton>
          ))}
        </List>
        <Box sx={{ mt: 2 }}>
          <ContextSelector />
        </Box>
      </Box>
      <Box sx={{ px: 2, mt: 3 }}>
        <ListItemButton
          onClick={logout}
          sx={{ px: 1, py: 0.5, borderRadius: "2px" }}
        >
          <ListItemText
            primary="Sign out"
            slotProps={{
              primary: { sx: { fontSize: 12, color: "text.secondary" } },
            }}
          />
        </ListItemButton>
      </Box>
    </Box>
  );
}

/** Mobile header — visible on xs only, no bottom tab bar (DESIGN.md). */
function MobileHeader() {
  const [open, setOpen] = useState(false);

  return (
    <Box sx={{ display: { xs: "block", md: "none" } }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          px: 2,
          py: 1.5,
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: "#FAFAF8",
        }}
      >
        <Typography
          sx={{
            fontFamily: fonts.mono,
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "0.08em",
            color: "primary.main",
          }}
        >
          OPENLNK
        </Typography>
        <Box
          onClick={() => setOpen(!open)}
          sx={{
            cursor: "pointer",
            fontFamily: fonts.mono,
            fontSize: 12,
            color: "text.secondary",
            px: 1,
            py: 0.5,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: "2px",
          }}
        >
          {open ? "CLOSE" : "MENU"}
        </Box>
      </Box>
      {open && (
        <Box
          sx={{
            bgcolor: "#FAFAF8",
            borderBottom: "1px solid",
            borderColor: "divider",
            px: 2,
            pb: 1.5,
          }}
        >
          <List disablePadding>
            {NAV_ITEMS.map((item) => (
              <ListItemButton
                key={item.path}
                component={NavLink}
                to={item.path}
                onClick={() => setOpen(false)}
                sx={{
                  px: 1,
                  py: 0.5,
                  "&.active": {
                    bgcolor: "primary.main",
                    color: "primary.contrastText",
                    "& .MuiListItemText-primary": {
                      color: "primary.contrastText",
                    },
                  },
                }}
              >
                <ListItemText
                  primary={item.label}
                  slotProps={{ primary: { sx: { fontSize: 14, fontWeight: 500 } } }}
                />
              </ListItemButton>
            ))}
          </List>
          <ContextSelector />
        </Box>
      )}
    </Box>
  );
}

function AppShell() {
  const { selectedContextId, isAuthenticated } = useAppStore();
  useContextSync(selectedContextId);

  return (
    <BrowserRouter>
      <Suspense
        fallback={
          <Typography sx={{ color: "text.secondary", py: 4, textAlign: "center" }}>
            {"\u2014"}
          </Typography>
        }
      >
        {!isAuthenticated ? (
          <Routes>
            <Route path="*" element={<LoginPage />} />
          </Routes>
        ) : (
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              minHeight: "100vh",
              bgcolor: "background.default",
            }}
          >
            <MobileHeader />
            <Sidebar />
            <Box
              component="main"
              sx={{ flex: 1, p: { xs: 2, md: 3 } }}
            >
              <Suspense
                fallback={
                  <Typography sx={{ color: "text.secondary", py: 4 }}>
                    {"\u2014"}
                  </Typography>
                }
              >
                <Routes>
                  <Route path="/" element={<DailyBriefPage />} />
                  <Route path="/inbox" element={<ExtractionInboxPage />} />
                  <Route path="/commitments" element={<CommitmentsPage />} />
              <Route path="/console" element={<ConsolePage />} />
                  <Route path="/commitments/new" element={<CreateCommitmentPage />} />
                  <Route path="/commitments/:id" element={<CommitmentDetailPage />} />
                </Routes>
              </Suspense>
            </Box>
          </Box>
        )}
      </Suspense>
    </BrowserRouter>
  );
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <AppShell />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
