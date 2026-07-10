# ADR-008 — Distribution Channel Risk and Fallback Strategy

Status: Accepted | Date: 2026-07-10 | Deciders: Founder/CEO + Technical Advisor

## Context

OpenLnk's growth engine depends on commitments flowing between parties who currently
communicate on WhatsApp. The link mechanic (ADR-005) uses openlnk.in links shared inside
WhatsApp threads. Three distribution risks require explicit mitigation:

1. **Meta's evolving policy on AI in WA**: Meta banned general-purpose AI assistants from
   the WhatsApp Business Platform effective 2026-01-15. Future policy changes could restrict
   how openlnk.in links are shared or previewed inside WA, or how the WA Business API is
   used for commitment-related messages.
2. **WA in-app webview restrictions**: The link mechanic depends on the WhatsApp in-app
   webview rendering the web-thread correctly (ADR-005). WA could restrict webview
   capabilities (localStorage, PWA features, deep-link handling) in future iOS/Android
   updates.
3. **SMS/OTP cost exposure**: OTP delivery via MSG91 is on the critical authentication path.
   A MSG91 outage or pricing spike has no fallback today.

## Decision

### §Channel Dependency Acknowledgment

OpenLnk is **messenger-first** (ADR confirmed in CEO review, 2026-07-10). Building a
new messenger that lives alongside WhatsApp is the chosen strategy. OpenLnk does NOT
depend on WhatsApp Business API for its core product — center owners and parents
communicate inside OpenLnk threads. WhatsApp is the **discovery channel** (openlnk.in
links shared in WA) and the **loop-close channel** (WA loop-close mechanic, OL-103a).

### §Policy Risk Mitigation

The WA loop-close mechanic (E4 / OL-103a) uses client-side `wa.me` deep-links — this is
a standard WhatsApp Share URL, not the WhatsApp Business API. It requires no Meta approval
and is governed by the same terms as any Android/iOS app using WA's share intent. This is
meaningfully lower risk than the Business API.

If Meta restricts `wa.me` deep-links in the future (low probability; this would break
millions of apps globally), the fallback is SMS/email delivery of the confirmation message
— the same text, different channel.

### §Link Discovery Fallback

If WA in-app webview restricts localStorage or PWA capabilities, the web-thread (ADR-005)
falls back to cookie-based session (already designed). If deep-links stop opening inside WA
webview, the link still opens in the system browser — the user experience degrades (loses
in-app seamlessness) but the product continues to function.

**Pre-flight blocker** (Gate 3 entry): A WA in-app webview prototype MUST be tested on
a physical Android device (Moto G-class or equivalent) before Gate 3 link mechanic is
deployed to the first parent. This is already noted in the eng review TODO list.

### §SMS/OTP Fallback Provider

OTP delivery for authentication (OL-146a) uses MSG91 as primary. A secondary provider
(Kaleyra or Twilio, configured in Infisical) MUST be tested in staging before Gate 2
deployment. The API adapter MUST implement a circuit breaker: if MSG91 returns errors for
≥3 consecutive OTP requests within 60 seconds, fail over to the secondary provider and
alert via Sentry.

### §Future Distribution Optionality

Post-Gate 5, if WhatsApp distribution becomes structurally blocked:
- Email/SMS commitment links: `openlnk.in/t/{token}` links work over any channel that
  carries a URL. The web-thread is channel-agnostic by design.
- MCP connectors: ADR-001 §Interfaces is designed for additive connectors. A future
  connector that extracts commitments from email threads or SMS is architecturally possible
  without a rewrite.
- Native notification channel: At Gate 4+, the mobile app's push notification channel
  (FCM/APNs) is a WA-independent retention path for installed users.

## Consequences

- **Positive**: The core product (commitment tracking, ledger, daily brief) is NOT
  WhatsApp-dependent. WA is the acquisition channel, not the product surface. A WA policy
  change would slow user acquisition, not break the product.
- **Negative**: The link mechanic's first-time user experience is meaningfully better inside
  the WA in-app webview than in a system browser. Any WA restriction to the webview would
  degrade the Gate 3 funnel metrics (open rate, return rate) — possibly below the ≥50%
  open target.
- **Monitor**: Monthly check on Meta's WA Business Platform policy changelog as part of
  the BLOCKED.md standing review. Escalate to BLOCKED.md if any policy change affects
  openlnk.in link behavior in WA.
