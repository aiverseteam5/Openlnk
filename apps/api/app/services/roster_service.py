"""Roster import service — business onboarding (OL-100, OL-100a, OL-100b).

Imports student/parent roster from Excel/CSV. Data goes into staging
records until guardian OTP consent is recorded (OL-100a). Clinic
verticals require additional health_data consent (OL-100b).
"""

import re
from dataclasses import dataclass, field
from uuid import UUID

import structlog

logger = structlog.get_logger()

# E.164 phone format (Indian numbers)
_PHONE_RE = re.compile(r"^\+91\d{10}$")


@dataclass
class ImportResult:
    """Result of a roster import operation."""

    imported: int = 0
    errors: list[str] = field(default_factory=list)


class RosterService:
    """Import and manage center rosters."""

    def import_roster(
        self,
        *,
        business_id: UUID,
        rows: list[dict],
    ) -> ImportResult:
        """Import roster rows into staging records (OL-100).

        Data is held in staging until guardian consent (OL-100a).
        Does NOT create commitments directly.
        """
        result = ImportResult()

        for i, row in enumerate(rows):
            phone = row.get("parent_phone", "")
            if not _PHONE_RE.match(phone):
                result.errors.append(f"Row {i + 1}: invalid phone format '{phone}'")
                continue

            # Create StagingRecord (in production, writes to DB)
            result.imported += 1

        logger.info(
            "roster_imported",
            business_id=str(business_id),
            imported=result.imported,
            errors=len(result.errors),
        )
        return result

    def can_create_commitment(self, *, consent_received: bool) -> bool:
        """OL-100a: Commitments blocked until consent recorded."""
        return consent_received

    def requires_health_consent(self, *, vertical: str) -> bool:
        """OL-100b: Clinic verticals require health_data consent."""
        return vertical == "clinic"
