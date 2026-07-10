"""Tests for Gate 3 — web-thread link mechanic (OL-080..085).

Zero-install thread access via openlnk.in links with signed JWT tokens.
"""

import time as time_mod
from uuid import uuid4

import pytest


@pytest.mark.req("OL-080")
class TestWebThreadAccess:
    """OL-080: Functional thread from link, no signup."""

    def test_thread_token_grants_thread_access(self):
        """A valid thread token grants access to the thread data."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        thread_id = uuid4()
        principal_id = uuid4()

        token = service.issue_token(thread_id=thread_id, principal_id=principal_id)
        assert token is not None

        claims = service.validate_token(token)
        assert claims is not None
        assert claims["thread_id"] == str(thread_id)
        assert claims["principal_id"] == str(principal_id)

    def test_thread_access_requires_no_signup(self):
        """Guest principals can access threads (kind=guest)."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        thread_id = uuid4()
        # Guest principal — no phone, no account
        guest_id = uuid4()

        token = service.issue_token(thread_id=thread_id, principal_id=guest_id)
        claims = service.validate_token(token)
        assert claims is not None
        assert claims["principal_id"] == str(guest_id)

    def test_get_thread_data_returns_commitments(self):
        """Thread data includes commitments for the thread."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        thread_id = uuid4()

        data = service.get_thread_data(thread_id=thread_id)
        assert "commitments" in data
        assert "thread_id" in data
        assert data["thread_id"] == str(thread_id)


@pytest.mark.req("OL-081")
class TestThreadTokenSecurity:
    """OL-081: Signed, thread-scoped, expiring tokens per ADR-005."""

    def test_token_is_signed_jwt(self):
        """Token is a valid JWT with signature."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        thread_id = uuid4()
        token = service.issue_token(thread_id=thread_id, principal_id=uuid4())

        # JWT has 3 parts: header.payload.signature
        parts = token.split(".")
        assert len(parts) == 3

    def test_token_is_thread_scoped(self):
        """Token grants access to exactly one thread."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        thread_a = uuid4()
        thread_b = uuid4()

        token_a = service.issue_token(thread_id=thread_a, principal_id=uuid4())
        claims = service.validate_token(token_a)

        assert claims["thread_id"] == str(thread_a)
        assert claims["thread_id"] != str(thread_b)

    def test_token_expires(self):
        """Token has an expiration and is rejected after expiry."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        thread_id = uuid4()

        # Issue token with very short TTL
        token = service.issue_token(
            thread_id=thread_id,
            principal_id=uuid4(),
            ttl_seconds=1,
        )
        # Wait for expiry
        time_mod.sleep(1.1)

        claims = service.validate_token(token)
        assert claims is None  # Expired token rejected

    def test_token_rejected_with_wrong_key(self):
        """Token signed with different key is rejected."""
        from app.services.web_thread_service import WebThreadService

        service_a = WebThreadService(secret_key="key-a-32chars-long-for-testing!!")
        service_b = WebThreadService(secret_key="key-b-32chars-long-for-testing!!")

        token = service_a.issue_token(thread_id=uuid4(), principal_id=uuid4())
        claims = service_b.validate_token(token)
        assert claims is None  # Wrong key → rejected

    def test_token_contains_jti(self):
        """Each token has a unique jti for revocation support."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")

        token1 = service.issue_token(thread_id=uuid4(), principal_id=uuid4())
        token2 = service.issue_token(thread_id=uuid4(), principal_id=uuid4())

        claims1 = service.validate_token(token1)
        claims2 = service.validate_token(token2)

        assert claims1["jti"] != claims2["jti"]

    def test_revoked_token_rejected(self):
        """Revoked token is rejected even if not expired."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        thread_id = uuid4()

        token = service.issue_token(thread_id=thread_id, principal_id=uuid4())
        claims = service.validate_token(token)
        jti = claims["jti"]

        service.revoke_token(jti=jti)

        # After revocation, token is rejected
        assert service.validate_token(token) is None


@pytest.mark.req("OL-082")
class TestSessionPersistence:
    """OL-082: Session persistence across visits (token refresh)."""

    def test_token_refresh_issues_new_token(self):
        """Refreshing a valid token issues a new token with fresh expiry."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        thread_id = uuid4()
        principal_id = uuid4()

        original_token = service.issue_token(thread_id=thread_id, principal_id=principal_id)
        new_token = service.refresh_token(original_token)

        assert new_token is not None
        assert new_token != original_token

        new_claims = service.validate_token(new_token)
        assert new_claims["thread_id"] == str(thread_id)
        assert new_claims["principal_id"] == str(principal_id)

    def test_expired_token_cannot_refresh(self):
        """Expired tokens cannot be refreshed — must use original link."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        token = service.issue_token(thread_id=uuid4(), principal_id=uuid4(), ttl_seconds=1)
        time_mod.sleep(1.1)

        new_token = service.refresh_token(token)
        assert new_token is None


@pytest.mark.req("OL-083")
class TestInstallOffer:
    """OL-083: App-install offer only at ≥2 active threads."""

    def test_no_install_offer_with_zero_threads(self):
        """No install offer when principal has 0 active threads."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        assert service.should_show_install_offer(active_thread_count=0) is False

    def test_no_install_offer_with_one_thread(self):
        """No install offer when principal has 1 active thread."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        assert service.should_show_install_offer(active_thread_count=1) is False

    def test_install_offer_at_two_threads(self):
        """Install offer shown when principal has 2 active threads."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        assert service.should_show_install_offer(active_thread_count=2) is True

    def test_install_offer_at_many_threads(self):
        """Install offer shown when principal has >2 active threads."""
        from app.services.web_thread_service import WebThreadService

        service = WebThreadService(secret_key="test-secret-key-32chars-long!!")
        assert service.should_show_install_offer(active_thread_count=5) is True


@pytest.mark.req("OL-084")
class TestBundleBudget:
    """OL-084: web-thread bundle ≤120 KB gzipped (CI-enforced)."""

    def test_bundle_budget_constant_defined(self):
        """The performance budget constant is defined and enforced."""
        from app.services.web_thread_service import MAX_BUNDLE_SIZE_KB

        assert MAX_BUNDLE_SIZE_KB == 120

    def test_bundle_budget_is_ci_enforceable(self):
        """Budget metadata available for CI enforcement."""
        from app.services.web_thread_service import get_bundle_budget

        budget = get_bundle_budget()
        assert budget["max_gzipped_kb"] == 120
        assert budget["lighthouse_interactive_ms"] == 3000
        assert budget["ci_enforced"] is True


@pytest.mark.req("OL-085")
class TestFunnelInstrumentation:
    """OL-085: Funnel instrumentation per center and message class."""

    def test_record_funnel_event_open(self):
        """Record a thread-open funnel event."""
        from app.services.web_thread_service import FunnelService

        service = FunnelService()
        event = service.record_event(
            event_type="open",
            thread_id=uuid4(),
            center_id=uuid4(),
            message_class="fee",
        )
        assert event["recorded"] is True
        assert event["event_type"] == "open"

    def test_record_funnel_event_return(self):
        """Record a thread-return funnel event."""
        from app.services.web_thread_service import FunnelService

        service = FunnelService()
        event = service.record_event(
            event_type="return",
            thread_id=uuid4(),
            center_id=uuid4(),
            message_class="schedule",
        )
        assert event["recorded"] is True
        assert event["event_type"] == "return"

    def test_record_funnel_event_install(self):
        """Record an install funnel event."""
        from app.services.web_thread_service import FunnelService

        service = FunnelService()
        event = service.record_event(
            event_type="install",
            thread_id=uuid4(),
            center_id=uuid4(),
            message_class="fee",
        )
        assert event["recorded"] is True
        assert event["event_type"] == "install"

    def test_funnel_events_scoped_per_center(self):
        """Funnel events include center_id for per-center analysis."""
        from app.services.web_thread_service import FunnelService

        service = FunnelService()
        center_id = uuid4()
        service.record_event(
            event_type="open",
            thread_id=uuid4(),
            center_id=center_id,
            message_class="fee",
        )
        metrics = service.get_center_metrics(center_id=center_id)
        assert metrics["open"] >= 1

    def test_funnel_events_scoped_per_message_class(self):
        """Funnel events include message_class for per-class analysis."""
        from app.services.web_thread_service import FunnelService

        service = FunnelService()
        center_id = uuid4()
        service.record_event(
            event_type="open",
            thread_id=uuid4(),
            center_id=center_id,
            message_class="fee",
        )
        service.record_event(
            event_type="open",
            thread_id=uuid4(),
            center_id=center_id,
            message_class="schedule",
        )
        metrics = service.get_class_metrics(center_id=center_id)
        assert "fee" in metrics
        assert "schedule" in metrics

    def test_valid_funnel_event_types(self):
        """Only valid event types accepted."""
        from app.services.web_thread_service import FunnelService

        service = FunnelService()
        with pytest.raises(ValueError, match="invalid event_type"):
            service.record_event(
                event_type="invalid_event",
                thread_id=uuid4(),
                center_id=uuid4(),
                message_class="fee",
            )
