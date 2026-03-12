"""Ralph Loop artifact integrity tests."""

import json
from importlib import util
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RALPH_LOOP_DIR = REPO_ROOT / "scripts" / "ralphloop"
ARTIFACT_IO_PATH = RALPH_LOOP_DIR / "artifact_io.py"
SELF_REVIEW_PATH = RALPH_LOOP_DIR / "self_review.py"
RUN_PATH = RALPH_LOOP_DIR / "run.py"


def load_module(name: str, path: Path):
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_atomic_write_json_and_latest_bundle_resolution(tmp_path):
    artifact_io = load_module("artifact_io_test", ARTIFACT_IO_PATH)

    manifest_path = tmp_path / "bundles" / "bundle_20260309T120500Z_abc1234" / "manifest.json"
    artifact_io.atomic_write_json(
        manifest_path,
        {
            "bundle_id": "bundle_20260309T120500Z_abc1234",
            "summary_artifact": "summary.json",
        },
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["bundle_id"] == "bundle_20260309T120500Z_abc1234"

    latest = artifact_io.resolve_latest_bundle(tmp_path)
    assert latest is not None
    assert latest["bundle_id"] == "bundle_20260309T120500Z_abc1234"
    assert latest["summary_path"].endswith("summary.json")


def test_save_review_ignores_manual_score_override(tmp_path, monkeypatch):
    self_review = load_module("self_review_test", SELF_REVIEW_PATH)
    monkeypatch.setattr(self_review, "REVIEWS_DIR", tmp_path)
    monkeypatch.setattr(self_review, "REPO_ROOT", REPO_ROOT)

    review_data = {
        "summary": "Two checks passed, but one failed.",
        "score": 10,
        "checklist": [
            {
                "id": "T1",
                "check": "First check",
                "severity": "HIGH",
                "status": "PASS",
                "finding": "",
                "files_checked": ["a.py"],
            },
            {
                "id": "T2",
                "check": "Second check",
                "severity": "MEDIUM",
                "status": "FAIL",
                "finding": "needs work",
                "files_checked": ["b.py"],
            },
        ],
    }

    output = self_review.save_review("testing", review_data)

    assert output["computed_score"] == 5
    assert "score" not in output
    assert output["manual_score_input"] == 10
    assert "manual_score_override_ignored" in output["blockers"]

    saved = json.loads((tmp_path / "review_testing.json").read_text(encoding="utf-8"))
    assert saved["computed_score"] == 5
    assert saved["content_hash"].startswith("sha256:")


def test_run_loader_prefers_computed_score(tmp_path, monkeypatch):
    run_module = load_module("run_test", RUN_PATH)

    reviews_dir = tmp_path / "reviews"
    reviews_dir.mkdir(parents=True)
    (reviews_dir / "review_testing.json").write_text(
        json.dumps(
            {
                "computed_score": 4,
                "score": 10,
                "issues": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(run_module, "ARTIFACTS_DIR", tmp_path)
    assert run_module.load_ai_review_score() == 12
