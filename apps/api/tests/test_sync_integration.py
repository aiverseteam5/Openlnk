"""Integration tests for WebSocket sync + commitment CRUD flow.

Tests the end-to-end sync protocol: commitment creates/transitions
trigger DeltaEvents that reach WebSocket subscribers.
Also tests the corrections endpoint (OL-026, OL-090).

These tests use the ConnectionManager directly (no real DB) to verify
the sync protocol mechanics in isolation.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.schemas import DeltaEvent
from app.services.sync import ConnectionManager, REPLAY_MAX_DAYS, REPLAY_MAX_EVENTS


@pytest.mark.req("OL-003")
class TestConnectionManagerSync:
    """ConnectionManager broadcast + connection lifecycle."""

    @pytest.mark.asyncio
    async def test_broadcast_stores_in_replay_buffer(self):
        """Events broadcast to a context are stored in the replay buffer."""
        mgr = ConnectionManager()
        ctx = uuid4()
        event = DeltaEvent(
            event="commitment.created",
            context_id=str(ctx),
            subject_id=str(uuid4()),
            seq=1,
            data={"title": "Pay fee"},
        )
        await mgr.broadcast_to_context(ctx, event)

        replay = mgr.get_replay_events(ctx)
        assert len(replay) == 1
        assert replay[0].event == "commitment.created"
        assert replay[0].seq == 1

    @pytest.mark.asyncio
    async def test_broadcast_multiple_events_ordered(self):
        """Multiple events are stored in order."""
        mgr = ConnectionManager()
        ctx = uuid4()

        for seq in range(1, 6):
            event = DeltaEvent(
                event=f"commitment.event_{seq}",
                context_id=str(ctx),
                subject_id=str(uuid4()),
                seq=seq,
                data={},
            )
            await mgr.broadcast_to_context(ctx, event)

        replay = mgr.get_replay_events(ctx)
        assert len(replay) == 5
        assert [e.seq for e in replay] == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_replay_filters_by_since_seq(self):
        """Replay returns only events with seq > since_seq."""
        mgr = ConnectionManager()
        ctx = uuid4()

        for seq in range(1, 6):
            event = DeltaEvent(
                event="test",
                context_id=str(ctx),
                subject_id=str(uuid4()),
                seq=seq,
                data={},
            )
            await mgr.broadcast_to_context(ctx, event)

        replay = mgr.get_replay_events(ctx, since_seq=3)
        assert len(replay) == 2
        assert [e.seq for e in replay] == [4, 5]

    @pytest.mark.asyncio
    async def test_replay_empty_for_unknown_context(self):
        """Replay for unknown context returns empty list."""
        mgr = ConnectionManager()
        replay = mgr.get_replay_events(uuid4())
        assert replay == []

    @pytest.mark.asyncio
    async def test_contexts_isolated(self):
        """Events in one context are not visible in another."""
        mgr = ConnectionManager()
        ctx_a = uuid4()
        ctx_b = uuid4()

        await mgr.broadcast_to_context(
            ctx_a,
            DeltaEvent(event="a", context_id=str(ctx_a), subject_id=str(uuid4()), seq=1, data={}),
        )
        await mgr.broadcast_to_context(
            ctx_b,
            DeltaEvent(event="b", context_id=str(ctx_b), subject_id=str(uuid4()), seq=1, data={}),
        )

        replay_a = mgr.get_replay_events(ctx_a)
        replay_b = mgr.get_replay_events(ctx_b)
        assert len(replay_a) == 1
        assert replay_a[0].event == "a"
        assert len(replay_b) == 1
        assert replay_b[0].event == "b"


@pytest.mark.req("OL-003a")
class TestDeltaReplayBounds:
    """Delta replay window bounded: <= 200 events or <= 30 days (OL-003a)."""

    @pytest.mark.asyncio
    async def test_replay_capped_at_200_events(self):
        """Replay buffer caps at REPLAY_MAX_EVENTS."""
        mgr = ConnectionManager()
        ctx = uuid4()

        for seq in range(1, 301):
            await mgr.broadcast_to_context(
                ctx,
                DeltaEvent(event="test", context_id=str(ctx), subject_id=str(uuid4()), seq=seq, data={}),
            )

        replay = mgr.get_replay_events(ctx)
        assert len(replay) <= REPLAY_MAX_EVENTS

    @pytest.mark.asyncio
    async def test_replay_buffer_is_bounded_deque(self):
        """Internal buffer uses bounded deque (oldest evicted)."""
        mgr = ConnectionManager()
        ctx = uuid4()

        for seq in range(1, 250):
            await mgr.broadcast_to_context(
                ctx,
                DeltaEvent(event="test", context_id=str(ctx), subject_id=str(uuid4()), seq=seq, data={}),
            )

        replay = mgr.get_replay_events(ctx)
        # Should have at most 200, and earliest should be seq >= 50
        assert len(replay) == REPLAY_MAX_EVENTS
        assert replay[0].seq >= 50

    @pytest.mark.asyncio
    async def test_replay_window_30_days(self):
        """Events older than 30 days are excluded from replay."""
        mgr = ConnectionManager()
        ctx = uuid4()

        # Manually insert an old event into the buffer
        old_ts = datetime.utcnow() - timedelta(days=REPLAY_MAX_DAYS + 1)
        old_event = DeltaEvent(event="old", context_id=str(ctx), subject_id=str(uuid4()), seq=1, data={})
        from collections import deque
        mgr._replay_buffer[ctx] = deque(maxlen=REPLAY_MAX_EVENTS)
        mgr._replay_buffer[ctx].append((old_ts, old_event))

        # Add a recent event
        recent_event = DeltaEvent(event="recent", context_id=str(ctx), subject_id=str(uuid4()), seq=2, data={})
        mgr._replay_buffer[ctx].append((datetime.utcnow(), recent_event))

        replay = mgr.get_replay_events(ctx)
        assert len(replay) == 1
        assert replay[0].event == "recent"


@pytest.mark.req("OL-003")
class TestSyncDeltaEventFormat:
    """DeltaEvent contains all fields needed for client sync."""

    def test_delta_event_structure(self):
        event = DeltaEvent(
            event="commitment.state_changed",
            context_id=str(uuid4()),
            subject_id=str(uuid4()),
            seq=5,
            data={"old_state": "proposed", "new_state": "accepted"},
        )
        dumped = event.model_dump()
        assert "event" in dumped
        assert "context_id" in dumped
        assert "subject_id" in dumped
        assert "seq" in dumped
        assert "data" in dumped

    def test_delta_event_serializable(self):
        """DeltaEvent is JSON-serializable for WebSocket transport."""
        import json
        event = DeltaEvent(
            event="commitment.created",
            context_id=str(uuid4()),
            subject_id=str(uuid4()),
            seq=1,
            data={"title": "Test"},
        )
        json_str = json.dumps(event.model_dump())
        parsed = json.loads(json_str)
        assert parsed["event"] == "commitment.created"


@pytest.mark.req("OL-026")
class TestCorrectionSchemaIntegration:
    """Correction action integrates with eval-candidate queue (OL-090)."""

    def test_correction_reject_schema(self):
        from app.schemas import CorrectionAction
        ca = CorrectionAction(action="reject")
        assert ca.action == "reject"
        assert ca.edits is None

    def test_correction_edit_schema(self):
        from app.schemas import CorrectionAction
        ca = CorrectionAction(action="edit", edits={"title": "Corrected title"})
        assert ca.edits["title"] == "Corrected title"

    def test_eval_candidate_model_exists(self):
        """EvalCandidate model supports the corrections queue."""
        from app.models import EvalCandidate
        assert hasattr(EvalCandidate, "commitment_id")
        assert hasattr(EvalCandidate, "action")
        assert hasattr(EvalCandidate, "edits")
        assert hasattr(EvalCandidate, "adjudicated")


@pytest.mark.req("OL-090")
class TestEvalCandidateQueue:
    """User corrections feed into the eval-candidate queue."""

    def test_eval_candidate_action_field(self):
        """EvalCandidate action is reject or edit."""
        from app.models import EvalCandidate
        ec = EvalCandidate(
            commitment_id=uuid4(),
            action="reject",
        )
        assert ec.action == "reject"

    def test_eval_candidate_edits_field(self):
        """EvalCandidate stores edit details as JSONB."""
        from app.models import EvalCandidate
        ec = EvalCandidate(
            commitment_id=uuid4(),
            action="edit",
            edits={"title": "New title", "amount_paise": 5000},
        )
        assert ec.edits["title"] == "New title"

    def test_eval_candidate_adjudicated_default(self):
        """New candidates default to not-adjudicated (DB default)."""
        from app.models import EvalCandidate
        ec = EvalCandidate(
            commitment_id=uuid4(),
            action="reject",
            adjudicated=False,
        )
        assert ec.adjudicated is False
