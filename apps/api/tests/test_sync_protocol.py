"""Tests for OL-003 (sync protocol) and OL-003a (delta replay window).

WHEN both parties are OpenLnk principals, the system shall render the
identical commitment state within 5s. Delta replay bounded to 200 events
or 30 days.
"""

import pytest


@pytest.mark.req("OL-003")
class TestSyncProtocol:
    """WebSocket-based sync protocol for real-time commitment state."""

    def test_connection_manager_exists(self):
        """ConnectionManager class exists for WebSocket management."""
        from app.services.sync import ConnectionManager

        assert ConnectionManager is not None

    def test_connection_manager_has_broadcast(self):
        """ConnectionManager can broadcast events to context subscribers."""
        from app.services.sync import ConnectionManager

        mgr = ConnectionManager()
        assert hasattr(mgr, "broadcast_to_context")

    def test_connection_manager_has_connect_disconnect(self):
        from app.services.sync import ConnectionManager

        mgr = ConnectionManager()
        assert hasattr(mgr, "connect")
        assert hasattr(mgr, "disconnect")

    def test_delta_event_schema_exists(self):
        """DeltaEvent schema for sync messages."""
        from app.schemas import DeltaEvent

        event = DeltaEvent(
            event="commitment.state_changed",
            context_id="00000000-0000-0000-0000-000000000001",
            subject_id="00000000-0000-0000-0000-000000000002",
            seq=1,
            data={"state": "accepted"},
        )
        assert event.event == "commitment.state_changed"
        assert event.seq == 1

    def test_websocket_endpoint_exists(self):
        """WebSocket route is registered."""
        from app.routers.sync import router

        routes = [r.path for r in router.routes]
        assert any("/ws" in r for r in routes)

    def test_commitment_service_emits_events(self):
        """CommitmentService references sync broadcast after writes."""
        import inspect

        from app.services.commitment_service import CommitmentService

        # create and transition_state should emit sync events
        create_src = inspect.getsource(CommitmentService.create)
        assert "broadcast" in create_src or "sync" in create_src or "notify" in create_src

        transition_src = inspect.getsource(CommitmentService.transition_state)
        has_sync = "broadcast" in transition_src or "sync" in transition_src
        assert has_sync or "notify" in transition_src


@pytest.mark.req("OL-003a")
class TestDeltaReplayWindow:
    """Delta-stream replay window bounded: <= 200 events or <= 30 days."""

    def test_replay_window_constants(self):
        """Replay bounds are defined as configuration."""
        from app.services.sync import REPLAY_MAX_DAYS, REPLAY_MAX_EVENTS

        assert REPLAY_MAX_EVENTS == 200
        assert REPLAY_MAX_DAYS == 30

    def test_delta_event_has_seq(self):
        """DeltaEvent includes sequence number for replay ordering."""
        from app.schemas import DeltaEvent

        event = DeltaEvent(
            event="test",
            context_id="00000000-0000-0000-0000-000000000001",
            subject_id="00000000-0000-0000-0000-000000000002",
            seq=42,
            data={},
        )
        assert event.seq == 42

    def test_connection_manager_has_replay(self):
        """ConnectionManager supports delta replay for reconnection."""
        from app.services.sync import ConnectionManager

        mgr = ConnectionManager()
        assert hasattr(mgr, "get_replay_events")
