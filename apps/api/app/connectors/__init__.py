"""Connectors — external system integrations.

ConnectorABC Protocol (eng review C2):
- Connectors implement the ConnectorABC protocol
- MAY import: connectors/ submodules, packages/schema types
- MAY NOT import: services/, routers/ (enforced by import-linter CI)
- Adding a connector must never require touching services (ADR-001)
"""

from typing import Protocol


class ConnectorABC(Protocol):
    """Protocol that all connectors must implement.

    The connector receives raw input from an external system,
    normalizes it, and returns it for the service layer to process.
    Connectors hold zero business logic (CLAUDE.md).
    """

    async def receive_message(self, raw_payload: dict) -> dict:
        """Receive and normalize an external message.

        Returns a normalized dict that the extraction service can process.
        Must not call any service-layer code.
        """
        ...

    async def health_check(self) -> bool:
        """Check if the external system is reachable."""
        ...
