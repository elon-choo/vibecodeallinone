"""Tests for Ralph Loop trust bundle publication."""

from __future__ import annotations

import json
from importlib import util
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
TRUST_BUNDLE_PATH = REPO_ROOT / "scripts" / "ralphloop" / "trust_bundle.py"


def load_module(name: str, path: Path):
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_review_payload(status: str = "warn") -> dict:
    return {
        "perspective": "security",
        "status": status,
        "computed_score": 6,
        "issues": [
            {
                "severity": "MEDIUM",
                "description": "rate limiting not implemented",
            }
        ],
        "blockers": [],
    }


def make_score() -> dict:
    return {
        "total": 82,
        "stage1_gates": 30,
        "stage2_ai_review": 18,
        "stage3_e2e": 20,
        "stage4_release": 14,
        "max_possible": 100,
        "notes": "All stages active",
    }


def test_publish_bundle_writes_manifest_summary_history_and_evidence_ref(tmp_path):
    trust_bundle = load_module("trust_bundle_test", TRUST_BUNDLE_PATH)
    repo_root = tmp_path / "repo"
    artifacts_dir = repo_root / "artifacts"
    reviews_dir = artifacts_dir / "reviews"
    repo_root.mkdir()
    reviews_dir.mkdir(parents=True)
    (repo_root / "package.json").write_text(json.dumps({"version": "9.9.9"}), encoding="utf-8")
    (reviews_dir / "review_security.json").write_text(json.dumps(make_review_payload()), encoding="utf-8")
    (artifacts_dir / "e2e_score.json").write_text(
        json.dumps(
            {
                "total_score": 20,
                "max_score": 20,
                "checks": {"smoke_test": {"score": 5, "max": 5}},
            }
        ),
        encoding="utf-8",
    )

    gates = [
        {"gate": "G0_env", "severity": "CRITICAL", "status": "PASS", "issues": []},
        {"gate": "G1_lint", "severity": "HIGH", "status": "PASS", "issues": []},
    ]
    release_checks = [
        {"id": "R2_changelog", "status": "PASS", "hint": "CHANGELOG.md"},
        {"id": "R10_ci_badge", "status": "FAIL", "hint": "README badge"},
    ]

    published = trust_bundle.publish_bundle(
        repo_root=repo_root,
        artifacts_dir=artifacts_dir,
        gates=gates,
        release_checks=release_checks,
        score=make_score(),
    )

    assert published["manifest_path"].exists()
    assert published["summary_path"].exists()
    assert published["history_path"].exists()
    assert published["evidence_ref_path"].exists()

    manifest = json.loads(published["manifest_path"].read_text(encoding="utf-8"))
    summary = json.loads(published["summary_path"].read_text(encoding="utf-8"))
    evidence_ref = json.loads(published["evidence_ref_path"].read_text(encoding="utf-8"))
    latest = json.loads((artifacts_dir / "latest.json").read_text(encoding="utf-8"))
    history_lines = (artifacts_dir / "history.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert manifest["bundle_id"] == published["bundle_id"]
    assert summary["app_version"] == "9.9.9"
    assert summary["overall_status"] == "warn"
    assert evidence_ref["bundle_id"] == published["bundle_id"]
    assert latest["bundle_id"] == published["bundle_id"]
    assert len(history_lines) >= 6


def test_publish_bundle_marks_stale_review_inputs(tmp_path, monkeypatch):
    trust_bundle = load_module("trust_bundle_test_stale", TRUST_BUNDLE_PATH)
    repo_root = tmp_path / "repo"
    artifacts_dir = repo_root / "artifacts"
    reviews_dir = artifacts_dir / "reviews"
    repo_root.mkdir()
    reviews_dir.mkdir(parents=True)
    (repo_root / "package.json").write_text(json.dumps({"version": "1.2.3"}), encoding="utf-8")
    review_path = reviews_dir / "review_security.json"
    review_path.write_text(json.dumps(make_review_payload(status="pass")), encoding="utf-8")
    (artifacts_dir / "e2e_score.json").write_text(
        json.dumps({"total_score": 20, "max_score": 20, "checks": {"smoke_test": {"score": 5, "max": 5}}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        trust_bundle,
        "is_artifact_stale",
        lambda paths, _repo_root: any(Path(path).name.startswith("review_") for path in paths),
    )

    published = trust_bundle.publish_bundle(
        repo_root=repo_root,
        artifacts_dir=artifacts_dir,
        gates=[{"gate": "G0_env", "severity": "CRITICAL", "status": "PASS", "issues": []}],
        release_checks=[{"id": "R2_changelog", "status": "PASS", "hint": "CHANGELOG.md"}],
        score=make_score(),
    )

    quality_stage = json.loads((published["bundle_dir"] / "stage_quality_review.json").read_text(encoding="utf-8"))
    summary = json.loads(published["summary_path"].read_text(encoding="utf-8"))

    assert quality_stage["status"] == "stale"
    assert summary["overall_status"] == "stale"
