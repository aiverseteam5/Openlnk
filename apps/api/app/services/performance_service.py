"""Performance and observability — OL-140, OL-143.

API latency budgets and Sentry configuration.
"""

# OL-140: API latency budgets (excluding LLM paths)
READ_LATENCY_P95_MS = 400
WRITE_LATENCY_P95_MS = 800

# OL-143: Sentry required in all four apps
SENTRY_REQUIRED_APPS = ("api", "mobile", "web-owner", "web-thread")

# LLM paths excluded from latency budget
_LLM_PATH_PREFIXES = ("/v1/extract", "/v1/llm")


def is_llm_path(path: str) -> bool:
    """Check if a path is an LLM path (excluded from latency budget)."""
    return any(path.startswith(prefix) for prefix in _LLM_PATH_PREFIXES)


def get_sentry_config() -> dict:
    """Return Sentry configuration structure."""
    return {
        "dsn_env_var": "SENTRY_DSN",
        "traces_sample_rate": 0.1,
        "environment": "production",
        "send_default_pii": False,
    }
