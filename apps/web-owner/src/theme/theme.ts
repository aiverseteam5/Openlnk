/**
 * MUI theme — derived from DESIGN.md via @openlnk/ui tokens.
 *
 * DM Sans (UI) + JetBrains Mono (amounts/dates/IDs/state).
 * No shadows, no gradients, no dark mode.
 */

import { createTheme } from "@mui/material/styles";
import { colors, fonts } from "@openlnk/ui";

const theme = createTheme({
  palette: {
    primary: {
      main: colors.accent,
      dark: colors.accentHover,
      contrastText: "#FFFFFF",
    },
    background: {
      default: colors.bg,
      paper: colors.surface,
    },
    text: {
      primary: colors.textPrimary,
      secondary: colors.textMuted,
      disabled: colors.textDisabled,
    },
    divider: colors.border,
  },
  typography: {
    fontFamily: fonts.primary,
    h5: { fontWeight: 600, fontSize: 18, lineHeight: "24px" },
    h6: { fontWeight: 600, fontSize: 16, lineHeight: "22px" },
    body1: { fontWeight: 400, fontSize: 14, lineHeight: "20px" },
    body2: { fontWeight: 400, fontSize: 12, lineHeight: "16px" },
    button: { fontWeight: 500, textTransform: "none" },
  },
  shape: {
    borderRadius: 2,
  },
  shadows: Array(25).fill("none") as any, // DESIGN.md: no shadows
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          boxShadow: "none",
          "&:hover": { boxShadow: "none" },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: `1px solid ${colors.border}`,
          borderRadius: 2,
          boxShadow: "none",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: "none",
        },
      },
    },
  },
});

export default theme;
