/**
 * Web-owner app — React + MUI center console.
 *
 * DESIGN.md: #F5F2EC background, max-content 960px, DM Sans + JetBrains Mono.
 * No dark mode, no avatars, no skeleton loaders.
 */

import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, CssBaseline } from "@mui/material";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import theme from "./theme/theme";
import CommitmentsPage from "./pages/CommitmentsPage";
import CommitmentDetailPage from "./pages/CommitmentDetailPage";
import CreateCommitmentPage from "./pages/CreateCommitmentPage";
import DailyBriefPage from "./pages/DailyBriefPage";
import { useContextSync } from "./hooks/useContextSync";
import { useAppStore } from "./store/app";
import { fonts } from "@openlnk/ui";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

const NAV_ITEMS = [
  { label: "Daily Brief", path: "/" },
  { label: "Commitments", path: "/commitments" },
];

function Sidebar() {
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
      }}
    >
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
    </Box>
  );
}

function AppShell() {
  const { selectedContextId } = useAppStore();
  useContextSync(selectedContextId);

  return (
    <BrowserRouter>
      <Box
        sx={{
          display: "flex",
          minHeight: "100vh",
          bgcolor: "background.default",
        }}
      >
        <Sidebar />
        <Box
          component="main"
          sx={{ flex: 1, p: { xs: 2, md: 3 } }}
        >
          <Routes>
            <Route path="/" element={<DailyBriefPage />} />
            <Route path="/commitments" element={<CommitmentsPage />} />
            <Route path="/commitments/new" element={<CreateCommitmentPage />} />
            <Route path="/commitments/:id" element={<CommitmentDetailPage />} />
          </Routes>
        </Box>
      </Box>
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
