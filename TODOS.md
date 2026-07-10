# TODOS.md — OpenLnk

Backlog items surfaced during reviews. Each item has context so a future session
can pick it up without needing to re-derive the motivation.

---

## T-001 — LLM provider DPDP candidate identification

**What:** Identify a DPDP-compliant LLM provider for the extraction pipeline before Gate 2 field deployment.

**Why:** Gate 2 BLOCKED.md item "LLM provider DPDP compliance verified before Gate 2" requires legal review of data processing terms. OpenAI/Anthropic/Vertex AI all have different DPA postures for India; none have published DPDP-specific terms as of 2026-07-10. Legal review + term negotiation can take weeks to months. If no compliant cloud provider is available, the fallback is a local model — which changes the extraction precision target (97%) into an entirely different engineering problem requiring GPU infra.

**Pros:** Identifies the critical path early; avoids Gate 2 being blocked by a months-long legal process.

**Cons:** Requires legal counsel time + potentially significant cost if a DPA amendment is needed.

**Context:** ADR-007 §6 requires all personal data processing terms reviewed against DPDP before Gate 2. The extraction pipeline processes raw conversation content (messages, voice transcripts, camera OCR) which may contain minor children's names and health-adjacent data for clinics.

**Depends on:** TynkAI entity registration (needed to sign DPA), Gate 1 extraction pipeline selecting a specific model/provider to evaluate.

**Owner:** Vinod + legal counsel
**Start:** Gate 1 week 1 (parallel track)

---

## T-002 — Supabase connection pool configuration

**What:** Configure Supabase connection pooling (built-in pgbouncer on port 6543, or self-hosted) before Gate 2 deployment.

**Why:** asyncpg creates a connection pool per process. With 4 arq workers + 4 API processes + asyncpg pool_size=10, that is 80+ connections at startup — exceeds Supabase free tier (60) and approaches pro tier limit (200) with headroom for spikes. A connection limit error under load is a silent production failure (new requests hang until a connection frees).

**Pros:** Zero production incidents from connection exhaustion; enables horizontal scaling of API processes later.

**Cons:** Supabase's built-in pooler is transaction-mode by default (breaks session-level GUCs like `app.principal_id`); must use statement mode or self-host pgbouncer configured for session pooling.

**Context:** The RLS design uses `app.principal_id` GUC set per connection. Transaction-mode pgbouncer resets GUCs between transactions, which would break RLS. Session-mode pooling is required. Supabase's built-in pooler supports session mode as a config option; verify this before Gate 2.

**Depends on:** Supabase tier decision (free vs. pro), Gate 2 staging environment setup.

**Owner:** engineer (API track)
**Start:** Gate 1 late / Gate 2 entry

---

## T-003 — NativeWind v4 primitive audit against UI screens

**What:** Audit NativeWind v4 primitive compatibility against the 6 finalized UI screens before starting Gate 1 mobile implementation.

**Why:** NativeWind v4 (as of 2026-07-10) has documented issues with: `FlatList` (commitment card scroll list), `ScrollView` inside `SafeAreaView` (Owner Home daily brief body), dynamic class toggling (state-color 3px left bars that change based on commitment state). These patterns appear in Owner Home, Context View, and Commitment Detail screens. Discovering breakage mid-sprint costs 2-5 days and forces either an SDK downgrade or inline StyleSheet fallbacks.

**Pros:** Catches NativeWind v4 breakage before it blocks the mobile sprint; fallback plan (inline StyleSheet for specific components) is cheap if identified early.

**Cons:** ~2h investigation time before sprint starts.

**Context:** ADR-004 accepted NativeWind v4 explicitly; no fallback is specified. The audit should map each screen's state-color bar (3px left border) and commitment card list to specific RN primitives and verify v4 renders them correctly on Android.

**Depends on:** Gate 1 mobile track starting; finalized.html files for the 6 screens (source of truth in /root/.gstack/projects/Openlnk/designs/).

**Owner:** engineer (mobile track)
**Start:** Gate 1 mobile sprint start (day 1)
