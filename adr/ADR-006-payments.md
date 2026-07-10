# ADR-006 — Payments: UPI Intent Deep-links; Funds Never Touch OpenLnk

**Status:** Accepted (Gate 0) · **Locked so nobody "improves" it into a compliance problem.**

## Context
Differentiator D5: the promise carries the payment. But routing center↔parent fees through
OpenLnk accounts would make us a payment aggregator (RBI PA licensing territory) — wrong
fight at this stage.

## Decision
- **Center↔parent settlement:** UPI **intent deep-links** (`upi://pay?...`) resolving to the
  center's own VPA, embedded in fee/payment commitments (OL-010, OL-103). The nudge and the
  payment are one tap apart; money moves directly center↔parent. OpenLnk is a facilitator,
  never merchant of record, never in the funds flow.
- **Payment confirmation:** parent-reported + owner-confirmed at Propose rung (OL-104);
  automated reconciliation (bank/PSP webhooks) is explicitly post-Gate 5.
- **OpenLnk's own revenue:** Razorpay subscriptions for center billing, GST invoices
  (OL-106). Razorpay KYC lead time noted as an external dependency — start at entity
  registration, not at Gate 5.
- Lapsed subscription → owner read-only, parent access preserved 90 days (OL-107): a
  center's failure to pay us must never break a parent's ledger — that's D1 integrity.

## Consequences
+ Zero licensing burden; UPI-native differentiation no US player or BSP replicates cleanly.
− No automatic payment truth at MVP (self-reported); accepted — the ROI screenshot
  ("fees recovered") still lands because owners confirm receipts in-console.
