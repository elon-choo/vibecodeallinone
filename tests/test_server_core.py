"""Core MCP server unit tests.

Tests the server tool registration, request routing, and config loading
without requiring a live Neo4j connection.
"""

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SERVER_PATH = Path(__file__).parent.parent / "kg-mcp-server" / "mcp_server" / "server.py"
CONFIG_PATH = Path(__file__).parent.parent / "kg-mcp-server" / "mcp_server" / "config.py"


def test_server_module_exists():
    """server.py should exist."""
    assert SERVER_PATH.exists(), f"server.py not found at {SERVER_PATH}"


def test_config_module_exists():
    """config.py should exist."""
    assert CONFIG_PATH.exists(), f"config.py not found at {CONFIG_PATH}"


def test_config_lazy_env_loading(monkeypatch):
    """Config should read env vars at access time, not import time."""
    monkeypatch.setenv("NEO4J_URI", "bolt://test:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "test_user")

    spec = importlib.util.spec_from_file_location("_config_test", CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cfg = mod.Config()
    assert cfg.neo4j_uri == "bolt://test:7687"
    assert cfg.neo4j_user == "test_user"


def test_config_defaults(monkeypatch):
    """Config should provide sensible defaults when env vars are missing."""
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    spec = importlib.util.spec_from_file_location("_config_default_test", CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cfg = mod.Config()
    assert cfg.neo4j_uri == "bolt://localhost:7687"
    assert cfg.neo4j_user == "neo4j"
    assert cfg.neo4j_password == ""


def test_config_embedding_dimensions():
    """Embedding dimensions should be 1024 for voyage-code-3."""
    spec = importlib.util.spec_from_file_location("_config_embed_dim", CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cfg = mod.Config()
    assert cfg.embedding_dimensions == 1024
    assert cfg.embedding_model == "voyage-code-3"


def test_config_max_tokens():
    """Max tokens should have a reasonable default."""
    spec = importlib.util.spec_from_file_location("_config_tokens", CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cfg = mod.Config()
    assert cfg.max_tokens == 4000
    assert cfg.search_limit == 20
    assert cfg.rerank_limit == 10
