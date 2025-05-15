"""Tests for the configuration loading and parsing in config.py."""

from pathlib import Path

import importlib
import sys  # Import sys at the top
import pytest
from config import _int_env  # Import _int_env for testing


def _fresh_google_cfg(monkeypatch: pytest.MonkeyPatch):
    """Returns a new instance of GoogleConfig after clearing and re-importing the config module.

    This ensures that changes to environment variables or monkeypatched attributes within
    the config module (like BASE_DIR) are reflected for the test.
    """
    # Remove the module from sys.modules to force a re-import and re-execution of module-level code
    sys.modules.pop("config", None)
    cfg_module = importlib.import_module("config")
    return cfg_module.GoogleConfig()


def test_credentials_path_uses_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Tests that if the env var path for credentials doesn't exist, but a fallback
    in BASE_DIR does, the fallback is used.
    """
    # Create a temporary directory and a dummy "google_credentials.json" inside it
    base_dir = tmp_path / "proj"
    base_dir.mkdir()
    fallback_file = base_dir / "google_credentials.json"
    fallback_file.write_text("{}")

    # Set environment variable to a non-existent file within the temp base_dir
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(base_dir / "nonexistent.json"))

    # Re-import config and get a new GoogleConfig instance
    # Patch BASE_DIR in the freshly imported config module to our temp base_dir
    # This must be done *after* GoogleConfig is instantiated if it captures BASE_DIR at import time,
    # or *before* if GoogleConfig() reads BASE_DIR dynamically or if BASE_DIR affects _raw_path resolution.
    # The current _fresh_google_cfg reloads config, then GoogleConfig is made. So patch after.
    # No, BASE_DIR is module level, so it's set on import. Patch *before* _fresh_google_cfg ideally,
    # or patch the module instance after import *before* GoogleConfig() uses it.
    # The current _fresh_google_cfg instantiates GoogleConfig immediately. For more control,
    # it could return the module, then we patch, then we instantiate.
    # Given current _fresh_google_cfg, we must patch BASE_DIR on the re-imported module *before* GoogleConfig() is called, or on the instance.
    # The original code patches cfg_mod.BASE_DIR *after* google_cfg = _fresh_google_cfg(), which might be too late
    # if BASE_DIR is used by GoogleConfig upon instantiation through _raw_path logic.
    # Let's adjust to patch the module *before* instantiation if possible, or ensure instance patching is effective.

    # To ensure BASE_DIR is patched correctly for _raw_path resolution that happens
    # relative to BASE_DIR if GOOGLE_CREDENTIALS_PATH is relative (which it is by default):

    # 1. Monkeypatch BASE_DIR in the config module *before* GoogleConfig is created or _raw_path is resolved by it.
    # This is tricky with module-level `load_dotenv()` and `BASE_DIR` definition.
    # A robust way is to control the config module's state more directly.

    # Alternative approach: Ensure _raw_path is absolute for the test or that BASE_DIR is effectively patched.
    # The current _fresh_google_cfg reloads the module, so BASE_DIR is reset.
    # We need to patch it on the *newly loaded* module instance.

    sys.modules.pop("config", None)  # Ensure config is reloaded
    cfg_mod = importlib.import_module("config")
    monkeypatch.setattr(cfg_mod, "BASE_DIR", base_dir)
    google_cfg = cfg_mod.GoogleConfig()  # Now instantiate with patched BASE_DIR

    # Perform the test
    path = Path(google_cfg.credentials_path)
    assert (
        path == fallback_file
    ), f"Expected fallback path {fallback_file}, but got {path}"


def test_credentials_path_raises_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Tests that FileNotFoundError is raised if neither the env var path nor the fallback exist."""
    base_dir = tmp_path / "proj2"
    base_dir.mkdir()

    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(base_dir / "absent.json"))

    # Re-import config, patch BASE_DIR, then get GoogleConfig instance
    sys.modules.pop("config", None)  # Ensure config is reloaded
    cfg_mod = importlib.import_module("config")
    monkeypatch.setattr(cfg_mod, "BASE_DIR", base_dir)
    google_cfg = cfg_mod.GoogleConfig()  # Now instantiate with patched BASE_DIR

    with pytest.raises(FileNotFoundError):
        _ = google_cfg.credentials_path


def test_int_env(monkeypatch: pytest.MonkeyPatch):
    """Tests the _int_env helper function for parsing integers from environment variables."""
    # Correct number with extraneous characters
    monkeypatch.setenv("TEST_INT_VALID", "  42px")
    assert _int_env("TEST_INT_VALID", 0) == 42

    # Variable not set -> should return default
    monkeypatch.delenv("TEST_INT_MISSING", raising=False)
    assert _int_env("TEST_INT_MISSING", 5) == 5

    # Incorrect content -> should return default
    monkeypatch.setenv("TEST_INT_INVALID_CONTENT", "abc")
    assert _int_env("TEST_INT_INVALID_CONTENT", 7) == 7

    # Negative number
    monkeypatch.setenv("TEST_INT_NEGATIVE", "-100")
    assert _int_env("TEST_INT_NEGATIVE", 0) == -100

    # Number with leading/trailing spaces
    monkeypatch.setenv("TEST_INT_SPACES", "  123  ")
    assert _int_env("TEST_INT_SPACES", 0) == 123

    # Empty string -> should return default
    monkeypatch.setenv("TEST_INT_EMPTY", "")
    assert _int_env("TEST_INT_EMPTY", 9) == 9


# --- Tests for other Config Dataclasses ---


def test_telegram_config(monkeypatch: pytest.MonkeyPatch):
    """Tests TelegramConfig for default value and environment variable override."""
    # Test default value
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    sys.modules.pop("config", None)
    cfg_module_default = importlib.import_module("config")
    assert cfg_module_default.telegram.token == ""

    # Test environment variable override
    monkeypatch.setenv(
        "TELEGRAM_BOT_TOKEN", "test_token_123"
    )  # pragma: allowlist secret
    sys.modules.pop("config", None)
    cfg_module_env = importlib.import_module("config")
    assert cfg_module_env.telegram.token == "test_token_123"


def test_openai_config(monkeypatch: pytest.MonkeyPatch):
    """Tests OpenAIConfig for default values and environment variable overrides."""
    # Test default values
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MAX_RETRIES", raising=False)
    sys.modules.pop("config", None)
    cfg_module_default = importlib.import_module("config")
    assert cfg_module_default.openai_cfg.api_key == ""
    assert cfg_module_default.openai_cfg.model == "gpt-4o-mini"
    assert cfg_module_default.openai_cfg.max_retries == 2

    # Test environment variable overrides
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")  # pragma: allowlist secret
    monkeypatch.setenv("OPENAI_MODEL", "gpt-3.5-turbo")
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "5")
    sys.modules.pop("config", None)
    cfg_module_env = importlib.import_module("config")
    assert (
        cfg_module_env.openai_cfg.api_key == "test_openai_key"
    )  # pragma: allowlist secret
    assert (
        cfg_module_env.openai_cfg.model == "gpt-3.5-turbo"
    )  # pragma: allowlist secret
    assert cfg_module_env.openai_cfg.max_retries == 5


def test_scheduler_config(monkeypatch: pytest.MonkeyPatch):
    """Tests SchedulerConfig."""
    monkeypatch.delenv("SCHEDULER_TIMEZONE", raising=False)
    monkeypatch.delenv("MORNING_REMINDER_TIME", raising=False)
    monkeypatch.delenv("EVENING_REMINDER_TIME", raising=False)
    monkeypatch.delenv("MOTIVATION_INTERVAL_HOURS", raising=False)
    sys.modules.pop("config", None)
    cfg_def = importlib.import_module("config").scheduler_cfg
    assert cfg_def.timezone == "Europe/Moscow"
    assert cfg_def.morning_time == "08:00"
    assert cfg_def.evening_time == "20:00"
    assert cfg_def.motivation_interval_hours == 8

    monkeypatch.setenv("SCHEDULER_TIMEZONE", "America/New_York")
    monkeypatch.setenv("MORNING_REMINDER_TIME", "07:30")
    monkeypatch.setenv("EVENING_REMINDER_TIME", "21:30")
    monkeypatch.setenv("MOTIVATION_INTERVAL_HOURS", "4")
    sys.modules.pop("config", None)
    cfg_env = importlib.import_module("config").scheduler_cfg
    assert cfg_env.timezone == "America/New_York"
    assert cfg_env.morning_time == "07:30"
    assert cfg_env.evening_time == "21:30"
    assert cfg_env.motivation_interval_hours == 4


def test_logging_config(monkeypatch: pytest.MonkeyPatch):
    """Tests LoggingConfig."""
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    sys.modules.pop("config", None)
    cfg_def = importlib.import_module("config").logging_cfg
    assert cfg_def.level == "WARNING"
    # format is not from env, so not tested for env override here

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    sys.modules.pop("config", None)
    cfg_env = importlib.import_module("config").logging_cfg
    assert cfg_env.level == "DEBUG"


def test_ratelimiter_config(monkeypatch: pytest.MonkeyPatch):
    """Tests RateLimiterConfig."""
    monkeypatch.delenv("LLM_REQUESTS_PER_MINUTE", raising=False)
    monkeypatch.delenv("LLM_MAX_BURST", raising=False)
    sys.modules.pop("config", None)
    cfg_def = importlib.import_module("config").ratelimiter_cfg
    assert cfg_def.llm_requests_per_minute == 20
    assert cfg_def.llm_max_burst == 5

    monkeypatch.setenv("LLM_REQUESTS_PER_MINUTE", "30")
    monkeypatch.setenv("LLM_MAX_BURST", "10")
    sys.modules.pop("config", None)
    cfg_env = importlib.import_module("config").ratelimiter_cfg
    assert cfg_env.llm_requests_per_minute == 30
    assert cfg_env.llm_max_burst == 10
