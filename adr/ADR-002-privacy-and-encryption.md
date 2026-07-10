# ADR-002 — Privacy, Data Minimization, and Encryption

Status: Accepted | Date: 2026-07-10 | Deciders: Founder/CEO + Technical Advisor

## Context

OpenLnk processes communication that contains commitment-bearing content. The data privacy
design has two hard constraints:

1. **Extraction window**: Raw message text, audio, and images are passed to an LLM for
   extraction. These MUST NOT be persisted server-side beyond the extraction window.
2. **DPDP Act 2023**: India's data protection law requires verifiable consent for personal
   data processing, and stricter minimization for sensitive categories (child data,
   health data).

## Decision

### §Messages — Ephemeral Extraction Window

Raw message text, audio transcripts, and camera images used for commitment extraction:
- Are held **in-memory only** for the duration of the extraction job (≤ 60 seconds, OL-024).
- Are **never written to disk, database, or object storage** on the server side.
- The extraction worker receives the content via the task payload (arq job), processes it,
  writes only the extracted Commitment fields to Postgres, and discards the source.
- The arq job payload itself is held in Redis. Redis persistence (AOF/RDB) for extraction
  queues MUST be disabled; if Redis restarts, in-flight extraction jobs are re-queued
  from the client-side source pointer (provenance_ref), not replayed from Redis.

**What IS stored:**
- `commitments.provenance_ref`: a client-side pointer to the originating message/media
  (e.g., a message ID in the client's local store). This is opaque to the server — the
  server cannot reconstruct the original content from it.
- `commitments.prompt_hash` and `commitments.model_id`: for audit reproducibility (OL-027).
- `commitments.extraction_confidence`: the model's confidence score, not the content.

### §Thread Messages — Persistent Product History

Thread messages (the product's messaging surface) ARE stored persistently:
- `messages.body`: stored encrypted at rest (AES-256-GCM, key per household or business
  context). The encryption layer is the storage/Postgres extension layer; application code
  works with plaintext via a transparent column-level encryption implementation.
- `messages.media_ref`: client-held pointer only; media is stored client-side. The server
  never receives the original media bytes for message storage (only for the ephemeral
  extraction window, after which they are discarded).

### §Child-Linked Data (DPDP Act 2023 §9)

Data associated with children (student name, schedule, attendance-adjacent, fee-adjacent):
- Tagged with `guardian_consent_at` on `household_members`.
- Held in staging state until OTP-confirmed guardian consent (OL-100a).
- Subject to stricter minimization: no behavioral inference, no advertising signal.
- Stored with a separate encryption key per child context, rotatable on consent withdrawal.

### §Health-Adjacent Data — Clinic Context (OL-120a)

Clinic appointment commitments may contain health-adjacent fields (appointment time,
doctor name — but NOT diagnosis, medication, or clinical notes, which are out of scope):
- Require `health_data:<patient_ref>` consent event before processing.
- Commitment titles in clinic contexts MUST NOT contain diagnosis, medication names, or
  clinical condition language — enforced by extraction prompt constraints.
- Legal review of consent scope and stated processing purpose is REQUIRED before Gate 3
  clinic onboarding.

### §Erasure Semantics

On user account deletion:
- The commitment graph is **anonymized, not destroyed**: owner_id and counterparty_id
  pointers are replaced with a tombstone principal (kind='deleted'), preserving the
  counterparty's ledger.
- `messages.body` encryption keys for the deleting user's household are destroyed
  (key deletion = effective erasure without data destruction).
- `consent_events`, `audit_log` entries are retained for legal/regulatory compliance
  (DPDP allows retention where legally required).
- `principals` row is soft-deleted (phone_e164 nulled, display_name anonymized).

## Consequences

- **Positive**: No server-side raw content means no raw-content breach risk. Encryption at
  rest is column-level, transparent to application code.
- **Negative**: In-memory-only extraction means lost extractions on worker crash mid-job.
  Mitigation: arq exponential backoff re-queues from client-side provenance_ref (OL-028).
- **Open**: On-device extraction (future, Post-Gate 5) would eliminate the server-side
  extraction window entirely — revisit this ADR when on-device model benchmarks are run.
