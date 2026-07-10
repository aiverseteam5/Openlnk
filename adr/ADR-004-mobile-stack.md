# ADR-004 — Mobile: Expo (dev-client) + React Native + NativeWind v4

**Status:** Accepted (Gate 0)

## Context
Consumer app for P2/P3 on low-end Android; solo-velocity build with Claude Code fluency in
TypeScript/React; pilot phases need shipping fixes without Play Store review latency.

## Decision
- **Expo with custom dev-client** (not bare, not ejected): native modules (camera, audio,
  future on-device inference) planned from day one via config plugins.
- **EAS Build + EAS Update (OTA):** JS-layer fixes reach pilot parents in minutes during
  Gates 2–4. This capability alone justifies Expo.
- **NativeWind v4** for styling (Tailwind muscle memory from SocialBharat; Claude Code
  highly fluent). React Native Paper permitted for complex primitives only.
  *Tamagui rejected:* compiler complexity and release churn are the wrong risk for a
  nights-and-weekends velocity build.
- **Expo Router** for navigation; TanStack Query + Zustand for state; zod at boundaries.
- **Android-first ruthlessly.** Every perf/UX decision optimizes for Moto-G-class devices;
  iOS builds ride along via EAS but never drive decisions before Gate 5.
- SDK pinned per milestone; upgrades only at gate boundaries.

## Consequences
+ One language across all clients; OTA superpower during pilots; boring, debuggable styling.
− RN perf ceilings on ancient devices; mitigated by web-thread carrying the true low-end
  path (ADR-005) — the app is for converted users, the link is for everyone.
