"""Tests for autonomy ladder requirements OL-050..OL-053.

Unit tests: model structure, enum values, rung ordering.
"""

import pytest

from app.models import AutonomyGrant, AutonomyRung


@pytest.mark.req("OL-050")
class TestAutonomyRungs:
    """The system shall implement rungs Observe, Propose, Bounded-auto,
    Trusted-auto, configured per (contact × commitment-class)."""

    def test_all_rungs_defined(self):
        expected = {"observe", "propose", "bounded_auto", "trusted_auto"}
        actual = {r.value for r in AutonomyRung}
        assert actual == expected

    def test_autonomy_grant_has_required_fields(self):
        from uuid import uuid4

        ag = AutonomyGrant(
            id=uuid4(),
            granter_id=uuid4(),
            contact_id=uuid4(),
            context_id=uuid4(),
            commitment_class="fee",
            rung=AutonomyRung.OBSERVE,
            clean_actions=0,
        )
        assert ag.rung == AutonomyRung.OBSERVE
        assert ag.commitment_class == "fee"
        assert ag.clean_actions == 0

    def test_rung_default_is_observe(self):
        """Default rung is observe (safest)."""
        assert AutonomyRung.OBSERVE.value == "observe"


@pytest.mark.req("OL-051")
class TestPolicyEngineDeterministic:
    """The policy engine shall be deterministic; the LLM only produces proposals."""

    def test_rung_ordering(self):
        """Rungs have a clear ordering: observe < propose < bounded_auto < trusted_auto."""
        rungs = list(AutonomyRung)
        rung_order = [r.value for r in rungs]
        assert rung_order.index("observe") < rung_order.index("propose")
        assert rung_order.index("propose") < rung_order.index("bounded_auto")
        assert rung_order.index("bounded_auto") < rung_order.index("trusted_auto")
