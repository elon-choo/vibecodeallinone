#!/usr/bin/env python3
"""Release evidence bundle publication for Ralph Loop."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

RALPH_LOOP_DIR = Path(__file__).parent
if str(RALPH_LOOP_DIR) not in sys.path:
    sys.path.insert(0, str(RALPH_LOOP_DIR))

artifact_io = importlib.import_module("artifact_io")
SCHEMA_VERSION = artifact_io.SCHEMA_VERSION
append_jsonl = artifact_io.append_jsonl
atomic_write_json = artifact_io.atomic_write_json
git_commit = artifact_io.git_commit
git_tree_state = artifact_io.git_tree_state
hash_inputs = artifact_io.hash_inputs
hash_json_payload = artifact_io.hash_json_payload
is_artifact_stale = artifact_io.is_artifact_stale
read_json = artifact_io.read_json
relative_path = artifact_io.relative_path
review_score_value = artifact_io.review_score_value
utc_now_iso = artifact_io.utc_now_iso

STAGE_ORDER = [
    "machine_gates",
    "quality_review",
    "e2e_validation",
    "release_readiness",
]

STATUS_PRIORITY = {
    "invalid": 7,
    "stale": 6,
    "blocked": 5,
    "fail": 4,
    "not_run": 3,
    "warn": 2,
    "running": 1,
    "pass": 0,
}

CRITICAL_RELEASE_FAILURES = {"R2_changelog", "R3_license", "R4_contributing", "R9_security"}


def package_version(repo_root: Path) -> str:
    package_json = repo_root / "package.json"
    package_data = read_json(package_json, default={})
    if isinstance(package_data, dict):
        version = package_data.get("version")
        if isinstance(version, str) and version.strip():
            return version
    return "0.0.0-dev"


def release_channel(repo_root: Path) -> str:
    if git_tree_state(repo_root) == "dirty":
        return "local"
    return "internal"


def timestamp_slug(iso_timestamp: str) -> str:
    return iso_timestamp.replace("-", "").replace(":", "")


def bundle_id_for(iso_timestamp: str, current_commit: str) -> str:
    short_commit = current_commit[:7] if current_commit and current_commit != "unknown" else "unknown"
    return f"bundle_{timestamp_slug(iso_timestamp)}_{short_commit}"


def worst_status(statuses: list[str]) -> str:
    if not statuses:
        return "not_run"
    return max(statuses, key=lambda status: STATUS_PRIORITY.get(status, -1))


def trust_label(status: str) -> str:
    labels = {
        "pass": "Evidence verified",
        "warn": "Evidence incomplete",
        "fail": "Verification failed",
        "blocked": "Evidence blocked",
        "invalid": "Verification insufficient",
        "stale": "Evidence stale",
        "not_run": "Evidence pending",
        "running": "Evidence pending",
    }
    return labels.get(status, "Evidence pending")


def stage_highlight(stage_id: str, status: str, narrative: str) -> str:
    stage_name = stage_id.replace("_", " ")
    if status == "pass":
        return f"{stage_name} passed. {narrative}".strip()
    if status in {"warn", "not_run", "blocked", "running"}:
        return f"{stage_name} is incomplete. {narrative}".strip()
    if status == "stale":
        return f"{stage_name} evidence is stale. {narrative}".strip()
    return f"{stage_name} failed validation. {narrative}".strip()


def build_stage_result(
    *,
    repo_root: Path,
    bundle_id: str,
    run_id: str,
    created_at: str,
    stage_id: str,
    status: str,
    computed_score: int,
    max_score: int,
    judge_mode: str,
    narrative: str,
    warnings: list[str],
    blockers: list[str],
    artifact_refs: list[str],
    source_payload: Any,
) -> dict[str, Any]:
    current_commit = git_commit(repo_root)
    body = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "stage_result",
        "artifact_id": f"stage_{stage_id}_{timestamp_slug(created_at)}",
        "bundle_id": bundle_id,
        "run_id": run_id,
        "git_commit": current_commit,
        "git_tree_state": git_tree_state(repo_root),
        "inputs_hash": hash_inputs(
            {
                "stage_id": stage_id,
                "source_payload": source_payload,
                "artifact_refs": artifact_refs,
            }
        ),
        "created_at": created_at,
        "producer": "scripts/ralphloop/run.py",
        "visibility": "operator",
        "status": status,
        "stage_id": stage_id,
        "computed_score": computed_score,
        "max_score": max_score,
        "judge_mode": judge_mode,
        "narrative": narrative,
        "started_at": created_at,
        "completed_at": created_at,
        "warnings": warnings,
        "blockers": blockers,
        "artifact_refs": artifact_refs,
    }
    return {**body, "content_hash": hash_json_payload(body)}


def build_machine_gates_stage(
    repo_root: Path,
    artifacts_dir: Path,
    bundle_id: str,
    run_id: str,
    created_at: str,
    gates: list[dict[str, Any]],
    stage_score: int,
) -> dict[str, Any]:
    fail_gates = [gate["gate"] for gate in gates if gate.get("status") == "FAIL"]
    warn_gates = [gate["gate"] for gate in gates if gate.get("status") == "WARN"]
    if fail_gates:
        status = "fail"
    elif warn_gates:
        status = "warn"
    else:
        status = "pass"

    narrative = f"{len(gates) - len(fail_gates) - len(warn_gates)} gates passed; {len(fail_gates)} failed; {len(warn_gates)} warned."
    return build_stage_result(
        repo_root=repo_root,
        bundle_id=bundle_id,
        run_id=run_id,
        created_at=created_at,
        stage_id="machine_gates",
        status=status,
        computed_score=stage_score,
        max_score=30,
        judge_mode="machine_scan",
        narrative=narrative,
        warnings=warn_gates,
        blockers=fail_gates,
        artifact_refs=[relative_path(artifacts_dir / "gates.json", repo_root)],
        source_payload=gates,
    )


def build_quality_review_stage(
    repo_root: Path,
    artifacts_dir: Path,
    bundle_id: str,
    run_id: str,
    created_at: str,
    stage_score: int,
) -> dict[str, Any]:
    reviews_dir = artifacts_dir / "reviews"
    review_files = [path for path in sorted(reviews_dir.glob("review_*.json")) if "_raw" not in path.name]
    if not review_files:
        return build_stage_result(
            repo_root=repo_root,
            bundle_id=bundle_id,
            run_id=run_id,
            created_at=created_at,
            stage_id="quality_review",
            status="not_run",
            computed_score=0,
            max_score=30,
            judge_mode="review_missing",
            narrative="No review artifacts were published.",
            warnings=[],
            blockers=["review_artifacts_missing"],
            artifact_refs=[],
            source_payload={"reviews": []},
        )

    review_payloads: list[dict[str, Any]] = []
    review_statuses: list[str] = []
    warnings: list[str] = []
    blockers: list[str] = []
    weakest_name = "unknown"
    weakest_score = 10

    for review_file in review_files:
        payload = read_json(review_file, default={})
        if not isinstance(payload, dict):
            continue
        review_payloads.append(payload)
        review_status = payload.get("status", "warn")
        review_statuses.append(review_status)
        warnings.extend(issue.get("description", "") for issue in payload.get("issues", []) if issue.get("severity") in {"LOW", "MEDIUM"})
        blockers.extend(str(blocker) for blocker in payload.get("blockers", []))
        perspective = str(payload.get("perspective", review_file.stem.replace("review_", "")))
        perspective_score = review_score_value(payload)
        if perspective_score < weakest_score:
            weakest_name = perspective
            weakest_score = perspective_score

    stale = is_artifact_stale(review_files, repo_root)
    status = "stale" if stale else worst_status(review_statuses)
    narrative = f"{len(review_payloads)} perspectives aggregated; weakest area: {weakest_name} ({weakest_score}/10)."
    return build_stage_result(
        repo_root=repo_root,
        bundle_id=bundle_id,
        run_id=run_id,
        created_at=created_at,
        stage_id="quality_review",
        status=status,
        computed_score=stage_score,
        max_score=30,
        judge_mode="self_checklist_aggregate",
        narrative=narrative,
        warnings=[warning for warning in warnings if warning][:5],
        blockers=sorted(set(blockers)),
        artifact_refs=[relative_path(path, repo_root) for path in review_files],
        source_payload=review_payloads,
    )


def build_e2e_stage(
    repo_root: Path,
    artifacts_dir: Path,
    bundle_id: str,
    run_id: str,
    created_at: str,
) -> dict[str, Any]:
    e2e_path = artifacts_dir / "e2e_score.json"
    e2e_payload = read_json(e2e_path, default={})
    if not isinstance(e2e_payload, dict) or not e2e_path.exists():
        return build_stage_result(
            repo_root=repo_root,
            bundle_id=bundle_id,
            run_id=run_id,
            created_at=created_at,
            stage_id="e2e_validation",
            status="not_run",
            computed_score=0,
            max_score=20,
            judge_mode="e2e_missing",
            narrative="No E2E evidence was published.",
            warnings=[],
            blockers=["e2e_artifact_missing"],
            artifact_refs=[],
            source_payload={"checks": {}},
        )

    checks = e2e_payload.get("checks", {})
    zero_checks = [
        check_id
        for check_id, check in checks.items()
        if isinstance(check, dict) and int(check.get("max", 0)) > 0 and int(check.get("score", 0)) == 0
    ]
    stale = is_artifact_stale([e2e_path], repo_root)
    if stale:
        status = "stale"
    elif zero_checks:
        status = "fail"
    elif int(e2e_payload.get("total_score", 0)) < int(e2e_payload.get("max_score", 20)):
        status = "warn"
    else:
        status = "pass"

    narrative = f"{len(checks)} E2E checks recorded; {len(zero_checks)} scored zero."
    warnings = [str(check_id) for check_id in checks if check_id not in zero_checks and int(checks[check_id].get("score", 0)) < int(checks[check_id].get("max", 0))]
    return build_stage_result(
        repo_root=repo_root,
        bundle_id=bundle_id,
        run_id=run_id,
        created_at=created_at,
        stage_id="e2e_validation",
        status=status,
        computed_score=int(e2e_payload.get("total_score", 0)),
        max_score=int(e2e_payload.get("max_score", 20)),
        judge_mode="e2e_score",
        narrative=narrative,
        warnings=warnings,
        blockers=zero_checks,
        artifact_refs=[relative_path(e2e_path, repo_root)],
        source_payload=e2e_payload,
    )


def build_release_readiness_stage(
    repo_root: Path,
    bundle_id: str,
    run_id: str,
    created_at: str,
    release_checks: list[dict[str, Any]],
    stage_score: int,
) -> dict[str, Any]:
    failed_ids = [check["id"] for check in release_checks if check.get("status") == "FAIL"]
    if not release_checks:
        status = "blocked"
    elif not failed_ids:
        status = "pass"
    elif CRITICAL_RELEASE_FAILURES.intersection(failed_ids) or len(failed_ids) > 2:
        status = "fail"
    else:
        status = "warn"

    narrative = f"{len(release_checks) - len(failed_ids)}/{len(release_checks)} release checks passed."
    return build_stage_result(
        repo_root=repo_root,
        bundle_id=bundle_id,
        run_id=run_id,
        created_at=created_at,
        stage_id="release_readiness",
        status=status,
        computed_score=stage_score,
        max_score=20,
        judge_mode="release_gate",
        narrative=narrative,
        warnings=[],
        blockers=failed_ids,
        artifact_refs=[],
        source_payload=release_checks,
    )


def build_manifest(
    *,
    repo_root: Path,
    bundle_id: str,
    run_id: str,
    created_at: str,
    app_version: str,
    channel: str,
    overall_status: str,
    stage_artifacts: dict[str, str],
    summary_artifact: str,
) -> dict[str, Any]:
    body = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "bundle_manifest",
        "artifact_id": f"manifest_{timestamp_slug(created_at)}",
        "bundle_id": bundle_id,
        "run_id": run_id,
        "git_commit": git_commit(repo_root),
        "git_tree_state": git_tree_state(repo_root),
        "inputs_hash": hash_inputs(
            {
                "stage_order": STAGE_ORDER,
                "stage_artifacts": stage_artifacts,
                "summary_artifact": summary_artifact,
            }
        ),
        "created_at": created_at,
        "producer": "scripts/ralphloop/run.py",
        "visibility": "operator",
        "status": overall_status,
        "app_version": app_version,
        "release_channel": channel,
        "overall_status": overall_status,
        "stage_order": STAGE_ORDER,
        "stage_artifacts": stage_artifacts,
        "summary_artifact": summary_artifact,
    }
    return {**body, "content_hash": hash_json_payload(body)}


def build_summary(
    *,
    repo_root: Path,
    bundle_id: str,
    run_id: str,
    created_at: str,
    app_version: str,
    channel: str,
    stage_results: list[dict[str, Any]],
    total_score: int,
) -> dict[str, Any]:
    overall_status = worst_status([stage_result["status"] for stage_result in stage_results])
    stage_statuses = [
        {
            "stage_id": stage_result["stage_id"],
            "status": stage_result["status"],
            "computed_score": stage_result["computed_score"],
            "max_score": stage_result["max_score"],
        }
        for stage_result in stage_results
    ]
    highlights = [stage_highlight(stage_result["stage_id"], stage_result["status"], stage_result["narrative"]) for stage_result in stage_results]
    body = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "evidence_summary",
        "artifact_id": f"summary_{timestamp_slug(created_at)}",
        "bundle_id": bundle_id,
        "run_id": run_id,
        "git_commit": git_commit(repo_root),
        "git_tree_state": git_tree_state(repo_root),
        "inputs_hash": hash_inputs({"stage_statuses": stage_statuses, "total_score": total_score}),
        "created_at": created_at,
        "producer": "scripts/ralphloop/run.py",
        "visibility": "public_summary",
        "status": overall_status,
        "app_version": app_version,
        "release_channel": channel,
        "generated_at": created_at,
        "overall_status": overall_status,
        "trust_label": trust_label(overall_status),
        "score": {
            "total": total_score,
            "max": 100,
        },
        "stage_statuses": stage_statuses,
        "highlights": highlights,
        "user_visible_controls": {
            "memory_export_supported": True,
            "memory_delete_supported": True,
            "latest_change_log_url": "/changelog",
            "evidence_detail_url": f"/trust/evidence/{bundle_id}",
        },
        "public_evidence_links": [
            {
                "label": "Quality report",
                "url": f"/trust/evidence/{bundle_id}",
            }
        ],
    }
    return {**body, "content_hash": hash_json_payload(body)}


def build_evidence_ref(summary: dict[str, Any], summary_path: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "app_version": summary["app_version"],
        "bundle_id": summary["bundle_id"],
        "summary_ref": relative_path(summary_path, repo_root),
        "overall_status": summary["overall_status"],
        "generated_at": summary["generated_at"],
    }


def history_event(
    *,
    repo_root: Path,
    bundle_id: str,
    run_id: str,
    created_at: str,
    event_type: str,
    status: str,
    artifact_refs: list[str],
    details: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "history_event",
        "artifact_id": f"{event_type}_{timestamp_slug(created_at)}",
        "bundle_id": bundle_id,
        "run_id": run_id,
        "git_commit": git_commit(repo_root),
        "git_tree_state": git_tree_state(repo_root),
        "inputs_hash": hash_inputs({"event_type": event_type, "details": details, "artifact_refs": artifact_refs}),
        "created_at": created_at,
        "producer": "scripts/ralphloop/run.py",
        "visibility": "operator",
        "status": status,
        "event_type": event_type,
        "artifact_refs": artifact_refs,
        "details": details,
    }
    return {**body, "content_hash": hash_json_payload(body)}


def publish_bundle(
    *,
    repo_root: Path,
    artifacts_dir: Path,
    gates: list[dict[str, Any]],
    release_checks: list[dict[str, Any]],
    score: dict[str, Any],
) -> dict[str, Any]:
    created_at = utc_now_iso()
    current_commit = git_commit(repo_root)
    run_id = f"run_{timestamp_slug(created_at)}"
    bundle_id = bundle_id_for(created_at, current_commit)
    app_version = package_version(repo_root)
    channel = release_channel(repo_root)

    bundle_dir = artifacts_dir / "bundles" / bundle_id
    history_path = artifacts_dir / "history.jsonl"
    evidence_refs_dir = artifacts_dir / "evidence_refs"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    evidence_refs_dir.mkdir(parents=True, exist_ok=True)

    append_jsonl(
        history_path,
        history_event(
            repo_root=repo_root,
            bundle_id=bundle_id,
            run_id=run_id,
            created_at=created_at,
            event_type="run_started",
            status="running",
            artifact_refs=[],
            details={"app_version": app_version},
        ),
    )

    stage_results = [
        build_machine_gates_stage(repo_root, artifacts_dir, bundle_id, run_id, created_at, gates, int(score["stage1_gates"])),
        build_quality_review_stage(repo_root, artifacts_dir, bundle_id, run_id, created_at, int(score["stage2_ai_review"])),
        build_e2e_stage(repo_root, artifacts_dir, bundle_id, run_id, created_at),
        build_release_readiness_stage(repo_root, bundle_id, run_id, created_at, release_checks, int(score["stage4_release"])),
    ]

    stage_artifacts: dict[str, str] = {}
    for stage_result in stage_results:
        stage_filename = f"stage_{stage_result['stage_id']}.json"
        stage_path = bundle_dir / stage_filename
        atomic_write_json(stage_path, stage_result)
        stage_artifacts[stage_result["stage_id"]] = stage_filename
        append_jsonl(
            history_path,
            history_event(
                repo_root=repo_root,
                bundle_id=bundle_id,
                run_id=run_id,
                created_at=created_at,
                event_type="stage_completed",
                status=stage_result["status"],
                artifact_refs=[relative_path(stage_path, repo_root)],
                details={
                    "stage_id": stage_result["stage_id"],
                    "computed_score": stage_result["computed_score"],
                },
            ),
        )

    summary = build_summary(
        repo_root=repo_root,
        bundle_id=bundle_id,
        run_id=run_id,
        created_at=created_at,
        app_version=app_version,
        channel=channel,
        stage_results=stage_results,
        total_score=int(score["total"]),
    )
    summary_path = bundle_dir / "summary.json"
    atomic_write_json(summary_path, summary)

    manifest = build_manifest(
        repo_root=repo_root,
        bundle_id=bundle_id,
        run_id=run_id,
        created_at=created_at,
        app_version=app_version,
        channel=channel,
        overall_status=summary["overall_status"],
        stage_artifacts=stage_artifacts,
        summary_artifact=summary_path.name,
    )
    manifest_path = bundle_dir / "manifest.json"
    atomic_write_json(manifest_path, manifest)

    evidence_ref = build_evidence_ref(summary, summary_path, repo_root)
    atomic_write_json(evidence_refs_dir / f"{app_version}.json", evidence_ref)
    atomic_write_json(evidence_refs_dir / "current.json", evidence_ref)

    latest_payload = {
        "bundle_id": bundle_id,
        "app_version": app_version,
        "overall_status": summary["overall_status"],
        "generated_at": summary["generated_at"],
        "manifest_path": relative_path(manifest_path, repo_root),
        "summary_path": relative_path(summary_path, repo_root),
    }
    atomic_write_json(artifacts_dir / "latest.json", latest_payload)

    append_jsonl(
        history_path,
        history_event(
            repo_root=repo_root,
            bundle_id=bundle_id,
            run_id=run_id,
            created_at=created_at,
            event_type="bundle_published",
            status=summary["overall_status"],
            artifact_refs=[relative_path(manifest_path, repo_root), relative_path(summary_path, repo_root)],
            details={"stage_order": STAGE_ORDER, "app_version": app_version},
        ),
    )
    append_jsonl(
        history_path,
        history_event(
            repo_root=repo_root,
            bundle_id=bundle_id,
            run_id=run_id,
            created_at=created_at,
            event_type="summary_exported",
            status=summary["overall_status"],
            artifact_refs=[relative_path(summary_path, repo_root), relative_path(evidence_refs_dir / f"{app_version}.json", repo_root)],
            details={"trust_label": summary["trust_label"]},
        ),
    )

    return {
        "bundle_id": bundle_id,
        "bundle_dir": bundle_dir,
        "manifest_path": manifest_path,
        "summary_path": summary_path,
        "history_path": history_path,
        "evidence_ref_path": evidence_refs_dir / f"{app_version}.json",
        "summary": summary,
        "manifest": manifest,
    }
