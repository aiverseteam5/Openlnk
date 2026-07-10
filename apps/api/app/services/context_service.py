"""Context service — auto-clustering and context management.

Contexts are auto-clustered from participant and content signal (OL-042).
Users can override the auto-assigned context.
"""

from uuid import UUID

from app.models import ContextKind


class ContextService:
    """Context auto-clustering and management."""

    def determine_context_kind(
        self,
        *,
        household_id: UUID | None,
        business_id: UUID | None,
    ) -> ContextKind:
        """Determine the context kind from the axis values.

        Enforces the one_axis constraint: exactly one of household_id
        or business_id must be set.
        """
        has_household = household_id is not None
        has_business = business_id is not None

        if has_household == has_business:
            msg = "Context must have exactly one of household_id or business_id"
            raise ValueError(msg)

        if has_household:
            return ContextKind.HOUSEHOLD
        return ContextKind.BUSINESS_BATCH

    def generate_label(
        self,
        *,
        kind: ContextKind,
        participant_names: list[str],
    ) -> str:
        """Auto-generate a context label from participants.

        Users can override this label at any time.
        """
        if not participant_names:
            return f"New {kind.value} context"

        if len(participant_names) <= 3:
            return ", ".join(participant_names)
        return f"{', '.join(participant_names[:3])} +{len(participant_names) - 3}"
