"""Tests for policy engine — OL-051..OL-053.

The policy engine is deterministic. The LLM only produces proposals.
Rungs control what happens with those proposals.
"""

import pytest

from app.models import AutonomyRung
from app.services.policy_engine import PolicyDecision, PolicyEngine


@pytest.mark.req("OL-051")
class TestPolicyEngineDeterministic:
    """The policy engine shall be deterministic; the LLM only proposes."""

    def test_policy_engine_is_deterministic(self):
        """Same inputs → same outputs, no randomness."""
        engine = PolicyEngine()
        decision1 = engine.evaluate(
            rung=AutonomyRung.OBSERVE,
            action_type="send_reminder",
            commitment_class="fee",
        )
        decision2 = engine.evaluate(
            rung=AutonomyRung.OBSERVE,
            action_type="send_reminder",
            commitment_class="fee",
        )
        assert decision1 == decision2

    def test_policy_engine_returns_decision(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.OBSERVE,
            action_type="send_reminder",
            commitment_class="fee",
        )
        assert isinstance(decision, PolicyDecision)


@pytest.mark.req("OL-052")
class TestObserveRung:
    """WHILE at rung Observe, the system shall extract and display
    but send nothing."""

    def test_observe_blocks_all_sends(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.OBSERVE,
            action_type="send_reminder",
            commitment_class="fee",
        )
        assert decision.allowed is False
        assert decision.reason == "observe_rung_blocks_all_sends"

    def test_observe_allows_extraction_display(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.OBSERVE,
            action_type="extract_and_display",
            commitment_class="fee",
        )
        assert decision.allowed is True


@pytest.mark.req("OL-053")
class TestProposeRung:
    """WHILE at rung Propose, the system shall draft messages/actions
    requiring explicit one-tap approval before send."""

    def test_propose_requires_approval(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.PROPOSE,
            action_type="send_reminder",
            commitment_class="fee",
        )
        assert decision.allowed is False
        assert decision.requires_approval is True
        assert decision.reason == "propose_rung_requires_approval"

    def test_propose_allows_display(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.PROPOSE,
            action_type="extract_and_display",
            commitment_class="fee",
        )
        assert decision.allowed is True
