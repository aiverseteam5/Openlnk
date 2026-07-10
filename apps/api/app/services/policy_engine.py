"""Policy engine — deterministic action gating per autonomy rung.

The LLM only produces proposals. The policy engine decides whether
to allow, require approval, or block based on the current rung.
This engine is purely deterministic (OL-051): same inputs → same outputs.
"""

from dataclasses import dataclass
from datetime import time

from app.models import AutonomyRung


@dataclass(frozen=True)
class PolicyDecision:
    """Result of a policy evaluation."""

    allowed: bool
    requires_approval: bool = False
    reason: str = ""


# Actions that are always allowed (display-only, no external effect)
_PASSIVE_ACTIONS = frozenset({"extract_and_display", "display", "log"})

# Whitelisted deterministic actions for bounded-auto (OL-054)
_BOUNDED_AUTO_WHITELIST = frozenset({"send_reminder", "send_confirmation"})


def _in_quiet_hours(
    current: time,
    start: time,
    end: time,
) -> bool:
    """Check if current time falls within quiet hours.

    Handles midnight wraparound (e.g., 22:00-07:00).
    """
    if start <= end:
        return start <= current < end
    # Wraps midnight: 22:00-07:00 → either >= 22:00 OR < 07:00
    return current >= start or current < end


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
        quiet_hours: tuple[time, time] | None = None,
        current_time: time | None = None,
    ) -> PolicyDecision:
        """Evaluate whether an action is allowed at the given rung.

        Args:
            rung: Current autonomy rung for this (contact x class) pair.
            action_type: Type of action (e.g., 'send_reminder').
            commitment_class: The commitment class (fee, schedule, etc.).
            quiet_hours: Optional (start, end) time tuple for quiet hours.
            current_time: Current time for quiet hours check.

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
            if action_type not in _BOUNDED_AUTO_WHITELIST:
                return PolicyDecision(
                    allowed=False,
                    requires_approval=True,
                    reason="bounded_auto_non_whitelisted",
                )
            # Quiet hours check (OL-054, OL-063)
            if quiet_hours and current_time is not None:
                if _in_quiet_hours(current_time, quiet_hours[0], quiet_hours[1]):
                    return PolicyDecision(
                        allowed=False,
                        reason="quiet_hours_active",
                    )
            return PolicyDecision(
                allowed=True,
                reason="bounded_auto_whitelisted_action",
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
