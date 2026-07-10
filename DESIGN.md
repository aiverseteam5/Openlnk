# Design System — OpenLnk

## Product Context
- **What this is:** Commitment-native communication — a signed contract rendered in digital ink. The atomic unit is the promise, not the message.
- **Who it's for:** P1 = Chennai tuition center owners (daily brief, ledger, propose flow); P3 = parents receiving zero-install commitment links via WhatsApp
- **Space/industry:** Indian B2B SaaS / fintech-adjacent. Peers: Classplus, Teachmint (ERPs), PhonePe/GPay (UPI fintech), Linear (serious software benchmark)
- **Project type:** Multi-surface — web-thread PWA (primary, perf-budgeted), mobile owner app (React Native + NativeWind v4), web-owner dashboard (React + MUI)

## Aesthetic Direction
- **Direction:** Industrial / Documentary
- **Decoration level:** Minimal — typography, ruled lines, and state color do all the work. No illustrations, no patterns, no gradients. Ever.
- **Mood:** A signed contract rendered in digital ink. The visual weight of a bank passbook, the precision of a notarized document. Every pixel earns its place by serving the commitment object. Design that tries to celebrate is wrong here — the record is the celebration.
- **The governing rule:** If a design decision would look at home in a consumer social app, it is wrong for OpenLnk. The reference objects are: a signed cheque, a bank passbook, a rental agreement, a court notice. These are objects people keep. Design for kept objects.
- **Competitive positioning:** Avoid orange (Classplus), purple (PhonePe), electric blue (GPay). The warm ivory + institutional blue combination is completely unoccupied in Indian fintech.

## Typography

- **Primary UI / Body:** DM Sans (400, 500, 600)
  - Rationale: Wide apertures survive JPEG compression and low-DPI screens on ₹10k Android phones. Geometric warmth without friendliness — not corporate (Helvetica), not playful (Poppins). Serious regional business software energy. Tamil-script-adjacent letterforms.
  - Loading: `https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap`

- **Data / Amounts / Dates / IDs / State badges:** JetBrains Mono (400, 600)
  - Rationale: `₹ 4,500.00` in mono anchors the eye. `DUE 15 OCT 2026` signals deadline, not suggestion. `CMT-0042` signals traceability. Every number aligns without CSS tricks. All state labels (`PROPOSED`, `ACCEPTED`, `BROKEN`) are set in mono — no icon replaces the word, ever.
  - Loading: `https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap`

- **No italic. No decorative display font. This is a ledger.**

### Type Scale (4px base grid)
| Role | Size | Line-height | Weight | Family |
|---|---|---|---|---|
| Commitment title | 18px | 24px | 600 | DM Sans |
| Section heading | 16px | 22px | 600 | DM Sans |
| Body / annotation | 14px | 20px | 400 | DM Sans |
| Amount (hero) | 20–24px | 28px | 600 | JetBrains Mono |
| Amount (card) | 14–16px | 20px | 600 | JetBrains Mono |
| Date / ID / State | 11–12px | 16px | 400/600 | JetBrains Mono |
| ALL-CAPS label | 11px | 14px | 600 | DM Sans, 0.08em tracking |
| Fine print / provenance | 11px | 16px | 400 | DM Sans |
| State badge text | 11px | 14px | 600 | JetBrains Mono, 0.1em tracking |

## Color

- **Approach:** Restrained — one accent, warm neutrals, semantic state colors. Color is rare and meaningful.

### Base tokens
| Token | Hex | Usage |
|---|---|---|
| `--bg` | `#F5F2EC` | Page background — aged paper, not clinical white. Reads as typeset. |
| `--surface` | `#FFFFFF` | Commitment card surface — stark white against warm bg creates document lift |
| `--surface-raised` | `#FAFAF8` | Secondary cards, sidebar, sheet backgrounds |
| `--border` | `#D6D0C4` | Card edges, row dividers — 1px, visible but not loud |
| `--mono-rule` | `#E8E3DA` | Horizontal rules within cards (ledger lines) |
| `--text-primary` | `#1A1814` | Near-black with warmth. Not pure `#000000` |
| `--text-muted` | `#6B6456` | Annotations, labels, provenance text |
| `--text-disabled` | `#AAA49A` | Inactive states, placeholders |

### Accent
| Token | Hex | Usage |
|---|---|---|
| `--accent` | `#1A4FBF` | Reserve Bank of India letterhead blue. Primary actions: Accept, Pay Now, Create Commitment. Not PhonePe purple, not GPay electric. The color of a signed cheque. |
| `--accent-subtle` | `#EDF1FB` | Accent hover/fill backgrounds, floating commitment card border |
| `--accent-hover` | `#153FA0` | Button hover state |

### Commitment state colors
| State | Text | Background | Left-bar | Label (mono) |
|---|---|---|---|---|
| `proposed` | `#374151` | `#F3F4F6` | `#374151` | `PROPOSED` |
| `accepted` | `#1A6B3C` | `#EAF4EE` | `#1A6B3C` | `ACCEPTED` |
| `in_progress` | `#1A6B3C` | `#EAF4EE` | `#1A6B3C` | `IN PROGRESS` |
| `overdue` | `#92600A` | `#FDF4E3` | `#92600A` | `OVERDUE` |
| `broken` | `#B91C1C` | `#FEF2F2` | `#B91C1C` | `BROKEN` |
| `fulfilled` | `#1A6B3C` | `#EAF4EE` | `#1A6B3C` | `FULFILLED` |
| `cancelled` | `#6B6456` | `#F5F2EC` | `#D6D0C4` | `CANCELLED` |

**What color is a commitment card?** `#FFFFFF` surface with 1px `#D6D0C4` border and a 3px left accent bar in the state color. No shadow (shadows are consumer app). The state color owns the left edge — you read state before you read title.

**What color is "Broken"?** `#B91C1C` text on `#FEF2F2`. No shaking animation, no emoji. The weight of a default notice, not a push notification.

**Dark mode:** None. Light mode only until Gate 5. Doubling the QA surface is not justified at this stage.

## Spacing

- **Base unit:** 4px
- **Density:** Compact (receipt density — this is not a wellness app; owners have 40 student families)
- **Card internal padding:** 12px horizontal / 10px vertical
- **Card-to-card gap:** 8px (list) / 4px (compact thread view)
- **Row height:** 20px line-height throughout
- **Target:** 6–7 commitment cards visible per screen on a 360px-wide phone without scrolling

### Scale
| Name | Value |
|---|---|
| 2xs | 2px |
| xs | 4px |
| sm | 8px |
| md | 12px |
| lg | 16px |
| xl | 24px |
| 2xl | 32px |
| 3xl | 48px |

## Layout

- **Approach:** Grid-disciplined — strict 4px grid, predictable row heights, no grid-breaking
- **Grid:** Full-bleed mobile (360px), 12-column on tablet/desktop, max-content 480px (web thread) / 960px (owner dashboard)
- **Border radius:** `2px` on cards and inputs. `4px` on buttons. `9999px` on state badges (pill). No bubbly radius — 2px is invisible enough to not signal "consumer app."
- **Card anatomy (top to bottom, left to right):**
  ```
  [3px STATE BAR] | [ID in mono, muted]           [STATE BADGE in mono]
                  | [COMMITMENT TITLE in DM Sans 600]
                  | [Counterparty · Class]          [AMOUNT in mono]
                  | [Provenance tag]                [DUE DATE in mono]
  ```
- **Commitment list:** full-width cards, 8px gap, no horizontal padding on mobile (full-bleed)
- **Bottom sheet** for commitment detail (standard Indian fintech pattern — users expect it)
- **Ledger and chat scroll independently** in the context view — never combine into one infinite scroll

## Motion

- **Approach:** None.
- State changes are **inline, timestamped, permanent audit entries** — not toasts, not animations, not badges.
  - `"Parent accepted on 10 Jul 2026 at 2:14 PM"` — signed with the actor, in the audit trail, forever.
- Toasts trivialize a two-party legal agreement. Do not use them for commitment events.
- Success confetti on commitment acceptance is a trust violation — it signals "game" not "contract."
- **Loading states:** Use `—` dashes in data positions (bank statement pattern), not skeleton loaders (skeleton screens are a UX apology for slow loads; the web-thread must be under 3s).
- **The only permitted transition:** page-level fade (150ms, ease-out) for sheet entry/exit. Nothing else.

## Component Conventions

### Commitment Card
- 3px left state bar (state color) — the first thing the eye reads
- `CMT-XXXX` ID in JetBrains Mono 10px muted, top-left
- Title in DM Sans 600, 14px
- Amount in JetBrains Mono 600, 14px, right-aligned
- Counterparty + provenance icon, 12px muted, bottom-left
- State badge ALL-CAPS, JetBrains Mono 11px, bottom-right
- Due date in JetBrains Mono, 11px, bottom-right (beside or below amount)
- Full-width tap target; no nested tappable elements inside the card row

### State Badge
- ALL-CAPS text, JetBrains Mono 600, 11px, 0.1em letter-spacing
- Background: state surface color; text: state text color; border-radius: 2px
- No icon accompanies it. The word is the signal. It survives 1.5× zoom.

### Buttons
- Primary: `#1A4FBF` background, `#FFFFFF` text, full-width on mobile
- Outline: `#1A4FBF` border + text, transparent background
- No gradient buttons. Ever.
- Label: DM Sans 600, 14px, no all-caps on buttons (all-caps is reserved for system labels)

### Navigation
- No bottom tab bar with icons + labels. This is not an app with five destinations.
- The owner surface has one primary object: commitments. Navigation is minimal.
- No unread message badges on chat icons. Badges belong on the "At Risk" count.

### Input / Chat
- Utilitarian: voice note button, text field, camera button. No emoji keyboard.
- Chat input sits at the very bottom of the screen — below the commitment ledger, always.
- No "Typing..." indicators. This is an async promise network, not a real-time chatroom.

### Avatars
- None. Counterparty identity is `[Name] / [Role] / [Phone]` in text.
- Legal documents do not have selfies in the header.

### Empty States
- One line: `No commitments. Create one.` — DM Sans 500, `#6B6456`, centered.
- No illustrated characters. No CTA styled as a primary action. Emptiness is a starting state, not a failure state. Treat it like a blank ledger page.

### Payments (UPI)
- UPI intent deep-link button: primary blue, full-width, "Pay ₹X via UPI"
- Appears only when commitment state reaches `accepted`
- After handoff to UPI app, show `PAYMENT PENDING VERIFICATION` in `--overdue-text` until webhook confirms
- Never show optimistic success for a financial commitment

## Surface-Specific Notes

### web-thread PWA (apps/web-thread)
- 120KB gzip budget enforced by `size-limit` CI — no design-system imports, Preact only, hand-rolled Tailwind
- Font loading: subset to Latin + Devanagari glyphs only; no full font families
- State colors must be inline CSS or Tailwind utilities — no runtime CSS-in-JS
- The web-thread is one screen: receipt view at top, action buttons in the middle, chat input at bottom

### mobile owner app (apps/mobile)
- NativeWind v4 — tokens map to Tailwind config
- DM Sans loaded via Expo Font
- JetBrains Mono loaded via Expo Font
- Avoid shadows (`shadow-*`) — use borders instead

### web-owner dashboard (apps/web-owner)
- React + MUI — override MUI theme with these tokens
- MUI `palette.primary.main`: `#1A4FBF`
- MUI `palette.background.default`: `#F5F2EC`
- MUI `palette.background.paper`: `#FFFFFF`
- MUI typography: override with DM Sans stack

## packages/ui Token Export

All tokens exported from `packages/ui` as CSS custom properties and as a JS/TS token object:

```ts
export const tokens = {
  color: {
    bg: '#F5F2EC',
    surface: '#FFFFFF',
    surfaceRaised: '#FAFAF8',
    border: '#D6D0C4',
    monoRule: '#E8E3DA',
    textPrimary: '#1A1814',
    textMuted: '#6B6456',
    textDisabled: '#AAA49A',
    accent: '#1A4FBF',
    accentSubtle: '#EDF1FB',
    accentHover: '#153FA0',
    state: {
      proposed:   { text: '#374151', bg: '#F3F4F6', bar: '#374151' },
      accepted:   { text: '#1A6B3C', bg: '#EAF4EE', bar: '#1A6B3C' },
      inProgress: { text: '#1A6B3C', bg: '#EAF4EE', bar: '#1A6B3C' },
      overdue:    { text: '#92600A', bg: '#FDF4E3', bar: '#92600A' },
      broken:     { text: '#B91C1C', bg: '#FEF2F2', bar: '#B91C1C' },
      fulfilled:  { text: '#1A6B3C', bg: '#EAF4EE', bar: '#1A6B3C' },
      cancelled:  { text: '#6B6456', bg: '#F5F2EC', bar: '#D6D0C4' },
    },
  },
  font: {
    sans: "'DM Sans', sans-serif",
    mono: "'JetBrains Mono', monospace",
  },
  spacing: {
    '2xs': '2px',  xs: '4px',  sm: '8px',
    md: '12px',    lg: '16px', xl: '24px',
    '2xl': '32px', '3xl': '48px',
  },
  radius: {
    card: '2px',
    btn: '4px',
    badge: '9999px',
  },
} as const
```

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-07-10 | DM Sans as primary UI font | Wide apertures for low-DPI Indian Android screens; not corporate, not playful; valid for serious regional business software |
| 2026-07-10 | JetBrains Mono for all data/amounts/dates/IDs/state | Numbers are data not prose; mono alignment; state labels in mono forces precise naming of every state |
| 2026-07-10 | `#1A4FBF` institutional blue as sole accent | Unoccupied in Indian fintech (PhonePe=purple, GPay=electric blue, Classplus=orange); reads as RBI/bank letterhead — "the color of a signed cheque" |
| 2026-07-10 | `#F5F2EC` warm ivory page background | Warm ivory reads as typeset/documentary; signals permanence; completely unoccupied in Indian fintech; slight risk of reading "old" but strongly reinforces the signed-document metaphor |
| 2026-07-10 | State as ALL-CAPS mono label, no icon | Every state named precisely; survives 1.5× zoom; forces product discipline — cannot hide ambiguous state behind an icon; no product in the competitive landscape does this |
| 2026-07-10 | No motion / no toasts / no success animations | State changes are timestamped audit entries, permanent, signed. UI does not celebrate. The record is the celebration. Trust signal > delight signal. |
| 2026-07-10 | No dark mode until Gate 5 | Doubles QA surface; not justified at this stage; light mode carries the documentary metaphor better |
| 2026-07-10 | 3px left accent bar on commitment cards, state color | State is the first thing the eye reads before title or amount; legal document status convention, not consumer badge convention |
| 2026-07-10 | Skeleton loaders → `—` dash placeholders | Bank statement pattern; skeletons are a UX apology for slow loads; web-thread must be <3s; dashes communicate "loading" without consumer-app aesthetic |
| 2026-07-10 | No avatars | Counterparty = text identity; legal documents don't have selfies in the header |
| 2026-07-10 | Cross-model validation | Design system reviewed against PRD + ADRs; independently proposed by a second model; three-model convergence on all major choices |
