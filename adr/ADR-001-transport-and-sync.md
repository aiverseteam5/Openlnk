# ADR-001 — Transport & Sync: Custom minimal protocol over Matrix

**Status:** Accepted (Gate 0) · **Owner:** Architecture · **Revisit:** post-Gate 5

## Context
OpenLnk needs real-time messaging between mobile, web-owner, and web-thread clients, on
flaky Indian mobile networks and low-end Android. Two candidate paths: adopt/fork Matrix
(open, federated, E2E via Olm/Megolm, bridging ecosystem) or build a minimal custom sync
protocol on our existing stack.

## Options considered
1. **Matrix (Synapse/Dendrite fork).** Pros: federation, E2E primitives solved, protocol
   credibility for the "open" brand. Cons: heavyweight ops for a 1-person team; our core
   object (the commitment) is not a Matrix event type — we'd fight the data model daily;
   E2E room encryption conflicts with server-side ephemeral extraction (ADR-002) at MVP;
   federation solves a problem we will not have before ~Gate 6.
2. **Custom minimal sync (chosen).** Postgres is the source of truth; FastAPI WebSockets +
   Redis pub/sub for push; long-poll fallback for hostile networks/webviews; monotonic
   per-context sequence numbers; client sends `last_seq`, server replays deltas. Idempotent
   by design with OL-007 keys.

## Decision
Build the custom minimal protocol. Messages and commitment-events share one delta stream
per context. No federation, no E2E room crypto at MVP; transport is TLS + signed tokens,
privacy guarantees come from ADR-002 (ephemeral extraction, no raw persistence) — an honest
story we can actually keep.

## The "open" check (name writes a check — this is how we cash it)
The protocol surface (`/v1` OpenAPI + the delta stream schema) is documented from day one in
`packages/schema`. Post-Gate 5, publishing this becomes the "OpenLnk protocol" story;
Matrix federation remains the documented future path if the protocol narrative matures.

## Interfaces rule
All external context sources (Google Calendar now; MCP connectors later) sit behind
`connectors/` interfaces. Adding a connector must never require touching services.

## Consequences
+ Weeks of ops and modeling saved; commitment object stays first-class.
+ Delta-stream replay gives offline-first mobile cheaply.
− We own delivery-guarantee bugs; mitigated by sequence-number replay tests (OL-003).
− No E2E at MVP; mitigated by ADR-002 and stated honestly in privacy copy.
