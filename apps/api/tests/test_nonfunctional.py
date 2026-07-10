"""Tests for non-functional requirements (OL-140..146a).

Rate limiting, Sentry wiring, secrets management, OTP auth, session tokens.
"""

from uuid import uuid4

import pytest


@pytest.mark.req("OL-140")
class TestAPILatency:
    """OL-140: API p95 latency < 400ms reads, < 800ms writes."""

    def test_latency_budgets_defined(self):
        """Latency budget constants are defined for enforcement."""
        from app.services.performance_service import (
            READ_LATENCY_P95_MS,
            WRITE_LATENCY_P95_MS,
        )

        assert READ_LATENCY_P95_MS == 400
        assert WRITE_LATENCY_P95_MS == 800

    def test_llm_paths_excluded_from_budget(self):
        """LLM paths are excluded from the latency budget."""
        from app.services.performance_service import is_llm_path

        assert is_llm_path("/v1/extract") is True
        assert is_llm_path("/v1/commitments") is False
        assert is_llm_path("/v1/commitments/123") is False


@pytest.mark.req("OL-143")
class TestSentryWiring:
    """OL-143: Sentry wired in all four apps before Gate 2."""

    def test_sentry_config_structure(self):
        """Sentry configuration structure is defined."""
        from app.services.performance_service import get_sentry_config

        config = get_sentry_config()
        assert "dsn_env_var" in config
        assert config["dsn_env_var"] == "SENTRY_DSN"
        assert config["traces_sample_rate"] <= 1.0
        assert config["traces_sample_rate"] > 0
        assert "environment" in config

    def test_sentry_required_apps(self):
        """Sentry must be wired in all four apps."""
        from app.services.performance_service import SENTRY_REQUIRED_APPS

        assert set(SENTRY_REQUIRED_APPS) == {"api", "mobile", "web-owner", "web-thread"}


@pytest.mark.req("OL-144")
class TestRateLimiting:
    """OL-144: Rate limiting at Caddy (IP) and FastAPI (per-token)."""

    def test_rate_limiter_per_token(self):
        """FastAPI rate limiter enforces per-token limits."""
        from app.services.rate_limit_service import RateLimitService

        service = RateLimitService()
        token_id = str(uuid4())

        # First N requests pass
        for _ in range(100):
            assert service.check_rate_limit(token_id=token_id, limit=100) is True

        # Next request blocked
        assert service.check_rate_limit(token_id=token_id, limit=100) is False

    def test_rate_limiter_per_thread_for_web_tokens(self):
        """Web-thread tokens additionally per-thread throttled."""
        from app.services.rate_limit_service import RateLimitService

        service = RateLimitService()
        thread_id = str(uuid4())

        # Per-thread limit is stricter
        for _ in range(50):
            assert service.check_thread_rate_limit(thread_id=thread_id, limit=50) is True

        assert service.check_thread_rate_limit(thread_id=thread_id, limit=50) is False

    def test_caddy_ip_rate_limit_config(self):
        """Caddy IP rate limit configuration is defined."""
        from app.services.rate_limit_service import get_caddy_rate_limit_config

        config = get_caddy_rate_limit_config()
        assert config["per_ip_requests_per_second"] > 0
        assert config["burst"] > 0


@pytest.mark.req("OL-145")
class TestSecretsManagement:
    """OL-145: No secrets in repo; shared secrets in Infisical."""

    def test_gitleaks_config_exists(self):
        """Gitleaks pre-commit configuration enforces no secrets in repo."""
        from app.services.security_service import get_gitleaks_config

        config = get_gitleaks_config()
        assert config["pre_commit_hook"] is True
        assert config["ci_enforced"] is True

    def test_secret_storage_provider(self):
        """Shared secrets managed via Infisical."""
        from app.services.security_service import get_secrets_provider

        provider = get_secrets_provider()
        assert provider["name"] == "infisical"
        assert provider["local_fallback"] == ".env"


@pytest.mark.req("OL-146")
class TestOTPAuth:
    """OL-146: OTP auth via MSG91 with cost telemetry."""

    def test_otp_send_via_msg91(self):
        """OTP sent via MSG91 as primary provider."""
        from app.services.auth_service import AuthService

        service = AuthService()
        result = service.send_otp(phone_e164="+919876543210")
        assert result["sent"] is True
        assert result["provider"] == "msg91"

    def test_otp_verification(self):
        """OTP can be verified."""
        from app.services.auth_service import AuthService

        service = AuthService()
        service.send_otp(phone_e164="+919876543210")

        # Verify with correct OTP
        result = service.verify_otp(phone_e164="+919876543210", otp="123456")
        assert result["verified"] is True

    def test_otp_cost_telemetry(self):
        """OTP cost is tracked for unit-economics sheet."""
        from app.services.auth_service import AuthService

        service = AuthService()
        service.send_otp(phone_e164="+919876543210")

        telemetry = service.get_cost_telemetry()
        assert telemetry["total_otps_sent"] == 1
        assert "cost_per_otp_inr" in telemetry


@pytest.mark.req("OL-146a")
class TestSessionTokens:
    """OL-146a: Access token 15-min TTL; refresh token 90-day TTL rotated on use."""

    def test_access_token_ttl(self):
        """Access token has 15-minute TTL."""
        from app.services.auth_service import AuthService

        service = AuthService()
        tokens = service.issue_session_tokens(principal_id=uuid4())
        assert tokens["access_token_ttl_minutes"] == 15

    def test_refresh_token_ttl(self):
        """Refresh token has 90-day TTL."""
        from app.services.auth_service import AuthService

        service = AuthService()
        tokens = service.issue_session_tokens(principal_id=uuid4())
        assert tokens["refresh_token_ttl_days"] == 90

    def test_refresh_token_rotated_on_use(self):
        """Refresh token is rotated on use (new token issued)."""
        from app.services.auth_service import AuthService

        service = AuthService()
        tokens = service.issue_session_tokens(principal_id=uuid4())
        original_refresh = tokens["refresh_token"]

        new_tokens = service.rotate_refresh_token(refresh_token=original_refresh)
        assert new_tokens is not None
        assert new_tokens["refresh_token"] != original_refresh

    def test_fallback_provider(self):
        """WHERE MSG91 is unreachable, fallback to secondary provider."""
        from app.services.auth_service import AuthService

        service = AuthService()
        result = service.send_otp(phone_e164="+919876543210", force_fallback=True)
        assert result["sent"] is True
        assert result["provider"] in ("kaleyra", "twilio")
