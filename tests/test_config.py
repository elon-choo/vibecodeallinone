"""Config dataclass environment variable loading tests."""

import os
import importlib.util
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "kg-mcp-server" / "mcp_server" / "config.py"


def _load_config():
    """Load config.py fresh (re-evaluates os.getenv defaults)."""
    spec = importlib.util.spec_from_file_location("_config_test", CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Config()


def test_config_defaults(monkeypatch):
    """Config has sensible defaults when no env vars set."""
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    cfg = _load_config()

    assert cfg.neo4j_uri == "bolt://localhost:7687"
    assert cfg.neo4j_user == "neo4j"
    assert cfg.neo4j_password == ""  # empty, not hardcoded
    assert cfg.max_tokens == 4000
    assert cfg.search_limit == 20
    assert cfg.embedding_model == "voyage-code-3"
    assert cfg.embedding_dimensions == 1024


def test_config_reads_env(monkeypatch):
    """Config picks up env var overrides."""
    monkeypatch.setenv("NEO4J_URI", "bolt://custom:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "testuser")
    monkeypatch.setenv("NEO4J_PASSWORD", "testpass")
    monkeypatch.setenv("VOYAGE_API_KEY", "voy-test-key")

    cfg = _load_config()

    assert cfg.neo4j_uri == "bolt://custom:7687"
    assert cfg.neo4j_user == "testuser"
    assert cfg.neo4j_password == "testpass"
    assert cfg.voyage_api_key == "voy-test-key"


def test_config_no_hardcoded_secrets(monkeypatch):
    """Ensure no hardcoded passwords in config defaults."""
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    cfg = _load_config()

    assert cfg.neo4j_password == "", "neo4j_password should default to empty string"
    assert cfg.voyage_api_key == "", "voyage_api_key should default to empty string"
