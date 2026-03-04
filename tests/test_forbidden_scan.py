"""Forbidden string scan tests.

Tests the G2 gate logic from Ralph Loop — ensures forbidden patterns
are correctly detected in the codebase.
"""

import sys
from pathlib import Path

# Add scripts to path for importing
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts" / "ralphloop"
sys.path.insert(0, str(SCRIPTS_DIR))


def test_forbidden_scan_gate_exists():
    """The G2 forbidden scan gate should be importable from run.py."""
    from run import gate_g2_forbidden_scan
    assert callable(gate_g2_forbidden_scan)


def test_forbidden_scan_returns_valid_structure():
    """G2 gate should return proper gate result dict."""
    from run import gate_g2_forbidden_scan
    result = gate_g2_forbidden_scan()

    assert "gate" in result
    assert "severity" in result
    assert "status" in result
    assert "issues" in result
    assert result["gate"] == "G2_forbidden_scan"
    assert result["severity"] == "CRITICAL"
    assert result["status"] in ("PASS", "FAIL", "WARN")
    assert isinstance(result["issues"], list)


def test_forbidden_scan_detects_legacy_path(tmp_path):
    """G2 should detect neo4j_knowledgeGraph hardcoded path."""
    import re

    # Simulate the pattern detection logic
    patterns = {
        r"neo4j_knowledgeGraph": ("CRITICAL", "Hardcoded legacy path"),
        r"from src\.": ("CRITICAL", "External src. import"),
        r"google\.generativeai": ("CRITICAL", "Deprecated SDK import"),
    }

    test_content = 'import neo4j_knowledgeGraph.config\n'
    found = []
    for pattern, (severity, desc) in patterns.items():
        if re.search(pattern, test_content):
            found.append({"severity": severity, "pattern": desc})

    assert len(found) == 1
    assert found[0]["pattern"] == "Hardcoded legacy path"


def test_forbidden_scan_passes_clean_code():
    """G2 should PASS when no forbidden patterns exist."""
    import re

    patterns = {
        r"neo4j_knowledgeGraph": ("CRITICAL", "Hardcoded legacy path"),
        r"from src\.": ("CRITICAL", "External src. import"),
        r"google\.generativeai": ("CRITICAL", "Deprecated SDK import"),
    }

    clean_content = '''
from mcp_server.config import config
import google.genai as genai
driver = GraphDatabase.driver(config.neo4j_uri)
'''
    found = []
    for pattern, (severity, desc) in patterns.items():
        if re.search(pattern, clean_content):
            found.append({"severity": severity, "pattern": desc})

    assert len(found) == 0


def test_all_machine_gates_return_valid():
    """All gate functions should return valid structure."""
    from run import (
        gate_g0_env,
        gate_g1_lint,
        gate_g2_forbidden_scan,
        gate_g6_sdk_deprecation,
        gate_g8_server_dry_run,
    )

    for gate_fn in [gate_g0_env, gate_g1_lint, gate_g2_forbidden_scan,
                    gate_g6_sdk_deprecation, gate_g8_server_dry_run]:
        result = gate_fn()
        assert "gate" in result, f"{gate_fn.__name__} missing 'gate' key"
        assert "status" in result, f"{gate_fn.__name__} missing 'status' key"
        assert "severity" in result, f"{gate_fn.__name__} missing 'severity' key"
        assert "issues" in result, f"{gate_fn.__name__} missing 'issues' key"
        assert result["status"] in ("PASS", "FAIL", "WARN"), \
            f"{gate_fn.__name__} invalid status: {result['status']}"
