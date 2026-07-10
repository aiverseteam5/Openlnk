"""Autonomy service — graduation, demotion, kill switch (OL-055..057).

Manages the autonomy ladder for (contact x class) pairs.
Graduation advances one rung after N clean actions over >= 14 days.
Demotion drops one rung on user correction. Kill switch resets all.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models import AutonomyRung

# OL-055: configurable, default 20
DEFAULT_GRADUATION_THRESHOLD = 20

# Minimum sliding window duration for graduation
GRADUATION_WINDOW_DAYS = 14

# Rung progression order (sacred rule: never skip rungs)
_RUNG_ORDER = [
    AutonomyRung.OBSERVE,
    AutonomyRung.PROPOSE,
    AutonomyRung.BOUNDED_AUTO,
    AutonomyRung.TRUSTED_AUTO,
]


@dataclass(frozen=True)
class GraduationResult:
    """Result of a graduation eligibility check."""

    eligible: bool
    next_rung: AutonomyRung | None = None
    clean_actions: int = 0
    days_in_window: int = 0
    reason: str = ""


@dataclass(frozen=True)
class DemotionResult:
    """Result of a demotion operation."""

    demoted: bool
    new_rung: AutonomyRung
    reason: str = ""


class AutonomyService:
    """Manages autonomy ladder transitions."""

    def __init__(self, graduation_threshold: int = DEFAULT_GRADUATION_THRESHOLD) -> None:
        self._threshold = graduation_threshold

    def check_graduation(
        self,
        *,
        current_rung: AutonomyRung,
        clean_actions: int,
        window_started: datetime,
    ) -> GraduationResult:
        """Check if a (contact x class) pair is eligible for graduation.

        OL-055: Requires N clean actions over >= 14 days.
        Shows the user the track record at the moment of graduation.
        """
        idx = _RUNG_ORDER.index(current_rung)
        days_in_window = (datetime.utcnow() - window_started).days

        # Already at top rung
        if idx >= len(_RUNG_ORDER) - 1:
            return GraduationResult(
                eligible=False,
                next_rung=None,
                clean_actions=clean_actions,
                days_in_window=days_in_window,
                reason="already_at_top_rung",
            )

        # Check sliding window duration
        if days_in_window < GRADUATION_WINDOW_DAYS:
            return GraduationResult(
                eligible=False,
                next_rung=_RUNG_ORDER[idx + 1],
                clean_actions=clean_actions,
                days_in_window=days_in_window,
                reason=f"window_too_short ({days_in_window}/{GRADUATION_WINDOW_DAYS} days)",
            )

        # Check clean action count
        if clean_actions < self._threshold:
            return GraduationResult(
                eligible=False,
                next_rung=_RUNG_ORDER[idx + 1],
                clean_actions=clean_actions,
                days_in_window=days_in_window,
                reason=f"insufficient_actions ({clean_actions}/{self._threshold})",
            )

        return GraduationResult(
            eligible=True,
            next_rung=_RUNG_ORDER[idx + 1],
            clean_actions=clean_actions,
            days_in_window=days_in_window,
            reason="eligible",
        )

    def demote(self, *, current_rung: AutonomyRung, cause: str) -> DemotionResult:
        """Demote a (contact x class) pair one rung (OL-056).

        Exactly one rung down on user correction. Never resets to observe
        unless already at propose.
        """
        idx = _RUNG_ORDER.index(current_rung)

        if idx <= 0:
            return DemotionResult(
                demoted=False,
                new_rung=current_rung,
                reason="already_at_bottom_rung",
            )

        return DemotionResult(
            demoted=True,
            new_rung=_RUNG_ORDER[idx - 1],
            reason=cause,
        )

    def kill_switch(self) -> AutonomyRung:
        """Per-context kill switch — revert all pairs to Observe (OL-057)."""
        return AutonomyRung.OBSERVE
