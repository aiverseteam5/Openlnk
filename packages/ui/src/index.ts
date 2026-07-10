/**
 * OpenLnk Design Tokens — exported from DESIGN.md
 *
 * Tokens, not components. DESIGN.md is the source of truth.
 * DM Sans (UI) + JetBrains Mono (amounts/dates/IDs/state).
 * Industrial / Documentary aesthetic.
 */

// ─── Base Colors ───

export const colors = {
  bg: "#F5F2EC",
  surface: "#FFFFFF",
  surfaceRaised: "#FAFAF8",
  border: "#D6D0C4",
  monoRule: "#E8E3DA",
  textPrimary: "#1A1814",
  textMuted: "#6B6456",
  textDisabled: "#AAA49A",

  accent: "#1A4FBF",
  accentSubtle: "#EDF1FB",
  accentHover: "#153FA0",
} as const;

// ─── Commitment State Colors ───

export type CommitmentState =
  | "proposed"
  | "accepted"
  | "in_progress"
  | "overdue"
  | "broken"
  | "fulfilled"
  | "cancelled";

export interface StateColors {
  text: string;
  background: string;
  leftBar: string;
  label: string;
}

export const stateColors: Record<CommitmentState, StateColors> = {
  proposed: {
    text: "#374151",
    background: "#F3F4F6",
    leftBar: "#374151",
    label: "PROPOSED",
  },
  accepted: {
    text: "#1A6B3C",
    background: "#EAF4EE",
    leftBar: "#1A6B3C",
    label: "ACCEPTED",
  },
  in_progress: {
    text: "#1A6B3C",
    background: "#EAF4EE",
    leftBar: "#1A6B3C",
    label: "IN PROGRESS",
  },
  overdue: {
    text: "#92600A",
    background: "#FDF4E3",
    leftBar: "#92600A",
    label: "OVERDUE",
  },
  broken: {
    text: "#B91C1C",
    background: "#FEF2F2",
    leftBar: "#B91C1C",
    label: "BROKEN",
  },
  fulfilled: {
    text: "#1A6B3C",
    background: "#EAF4EE",
    leftBar: "#1A6B3C",
    label: "FULFILLED",
  },
  cancelled: {
    text: "#6B6456",
    background: "#F5F2EC",
    leftBar: "#D6D0C4",
    label: "CANCELLED",
  },
} as const;

// ─── Typography ───

export const fonts = {
  primary: '"DM Sans", sans-serif',
  mono: '"JetBrains Mono", monospace',
} as const;

export const fontUrls = {
  dmSans:
    "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap",
  jetBrainsMono:
    "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap",
} as const;

export const typeScale = {
  commitmentTitle: { size: 18, lineHeight: 24, weight: 600, family: "primary" },
  sectionHeading: { size: 16, lineHeight: 22, weight: 600, family: "primary" },
  body: { size: 14, lineHeight: 20, weight: 400, family: "primary" },
  amountHero: { size: 22, lineHeight: 28, weight: 600, family: "mono" },
  amountCard: { size: 15, lineHeight: 20, weight: 600, family: "mono" },
  dateIdState: { size: 11, lineHeight: 16, weight: 600, family: "mono" },
  allCapsLabel: {
    size: 11,
    lineHeight: 14,
    weight: 600,
    family: "primary",
    letterSpacing: "0.08em",
  },
  finePrint: { size: 11, lineHeight: 16, weight: 400, family: "primary" },
  stateBadge: {
    size: 11,
    lineHeight: 14,
    weight: 600,
    family: "mono",
    letterSpacing: "0.1em",
  },
} as const;

// ─── Spacing (4px base grid) ───

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

// ─── Card ───

export const card = {
  borderRadius: 2,
  borderWidth: 1,
  borderColor: colors.border,
  stateBarWidth: 3,
  surface: colors.surface,
} as const;

// ─── Button ───

export const button = {
  borderRadius: 4,
  primary: {
    background: colors.accent,
    text: "#FFFFFF",
    hoverBackground: colors.accentHover,
  },
} as const;
