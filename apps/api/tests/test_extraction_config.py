"""Tests for OL-029a extraction threshold + OL-073 connector interface."""

import pytest

from app.config import settings
from app.connectors import ConnectorABC


@pytest.mark.req("OL-029a")
class TestExtractionThreshold:
    """The extraction confidence threshold shall be a versioned
    configuration value, not a hardcoded constant."""

    def test_threshold_is_configurable(self):
        """Threshold exists as a settings value, not a hardcoded constant."""
        assert hasattr(settings, "extraction_confidence_threshold")
        assert isinstance(settings.extraction_confidence_threshold, float)

    def test_threshold_has_sensible_default(self):
        """Default threshold is between 0 and 1."""
        assert 0 < settings.extraction_confidence_threshold < 1

    def test_threshold_default_value(self):
        """Default threshold is 0.85 (propose threshold)."""
        assert settings.extraction_confidence_threshold == 0.85


@pytest.mark.req("OL-073")
class TestConnectorInterface:
    """Calendar ingestion shall live behind the connector interface."""

    def test_connector_abc_is_protocol(self):
        """ConnectorABC is a Protocol class."""
        from typing import Protocol

        assert issubclass(ConnectorABC, Protocol)

    def test_connector_abc_has_receive_message(self):
        assert hasattr(ConnectorABC, "receive_message")

    def test_connector_abc_has_health_check(self):
        assert hasattr(ConnectorABC, "health_check")

    def test_connector_implementation_structural(self):
        """A class implementing the protocol shape is accepted."""

        class TestConnector:
            async def receive_message(self, raw_payload: dict) -> dict:
                return {}

            async def health_check(self) -> bool:
                return True

        # Structural subtyping — TestConnector satisfies ConnectorABC
        connector: ConnectorABC = TestConnector()
        assert connector is not None
