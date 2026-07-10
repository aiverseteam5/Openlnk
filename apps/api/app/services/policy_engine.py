"""Policy engine — deterministic action gating per autonomy rung.

The LLM only produces proposals. The policy engine decides whether
to allow, require approval, or block based on the current rung.
This engine is purely deterministic (OL-051): same inputs → same outputs.
"""

from dataclasses import dataclass

from app.models import AutonomyRung


@dataclass(frozen=True)
class PolicyDecision:
    """Result of a policy evaluation."""

    allowed: bool
    requires_approval: bool = False
    reason: str = ""


# Actions that are always allowed (display-only, no external effect)
_PASSIVE_ACTIONS = frozenset({"extract_and_display", "display", "log"})


class PolicyEngine:
    """Deterministic policy engine (ADR-003).

    Evaluates whether an action is allowed at the current autonomy rung.
    The LLM proposes; the policy engine decides. No randomness, no learning.
    """

    def evaluate(
        self,
        *,
        rung: AutonomyRung,
        action_type: str,
        commitment_class: str,
    ) -> PolicyDecision:
        """Evaluate whether an action is allowed at the given rung.

        Args:
            rung: Current autonomy rung for this (contact x class) pair.
            action_type: Type of action (e.g., 'send_reminder', 'extract_and_display').
            commitment_class: The commitment class (fee, schedule, task, etc.).

        Returns:
            PolicyDecision with allowed/requires_approval/reason.
        """
        # Passive actions are always allowed regardless of rung
        if action_type in _PASSIVE_ACTIONS:
            return PolicyDecision(allowed=True, reason="passive_action")

        if rung == AutonomyRung.OBSERVE:
            return PolicyDecision(
                allowed=False,
                reason="observe_rung_blocks_all_sends",
            )

        if rung == AutonomyRung.PROPOSE:
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                reason="propose_rung_requires_approval",
            )

        if rung == AutonomyRung.BOUNDED_AUTO:
            # Only whitelisted deterministic actions allowed (OL-054)
            if action_type in {"send_reminder", "send_confirmation"}:
                return PolicyDecision(
                    allowed=True,
                    reason="bounded_auto_whitelisted_action",
                )
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                reason="bounded_auto_non_whitelisted",
            )

        if rung == AutonomyRung.TRUSTED_AUTO:
            return PolicyDecision(
                allowed=True,
                reason="trusted_auto_allows_all",
            )

        return PolicyDecision(
            allowed=False,
            reason="unknown_rung",
        )
