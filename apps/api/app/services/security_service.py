"""Security service — OL-145.

Secrets management: gitleaks pre-commit, Infisical for shared secrets.
"""


def get_gitleaks_config() -> dict:
    """Return gitleaks configuration for secret detection."""
    return {
        "pre_commit_hook": True,
        "ci_enforced": True,
        "config_file": ".gitleaks.toml",
    }


def get_secrets_provider() -> dict:
    """Return the secrets management provider configuration."""
    return {
        "name": "infisical",
        "local_fallback": ".env",
        "environment_variable_prefix": "OPENLNK_",
    }
