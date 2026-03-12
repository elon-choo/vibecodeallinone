"""Trust summary resolution for assistant-api."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from .config import PROJECT_ROOT, Settings
from .models import EvidenceRef, EvidenceSummary, StageStatus, TrustBundleResponse, TrustCurrentResponse
from .store import SQLiteAssistantStore

RALPH_LOOP_DIR = PROJECT_ROOT / "scripts" / "ralphloop"
if str(RALPH_LOOP_DIR) not in sys.path:
    sys.path.insert(0, str(RALPH_LOOP_DIR))

artifact_io = importlib.import_module("artifact_io")
read_json = artifact_io.read_json
resolve_latest_bundle = artifact_io.resolve_latest_bundle
is_artifact_stale = artifact_io.is_artifact_stale


class TrustResolver:
    def __init__(self, settings: Settings, store: SQLiteAssistantStore):
        self.settings = settings
        self.store = store

    def get_current(self, app_version: str) -> TrustCurrentResponse | None:
        evidence_ref = (
            self.store.get_evidence_ref(app_version)
            or self._load_file_evidence_ref(app_version)
            or self._build_latest_evidence_ref(app_version)
        )
        if evidence_ref is None:
            return None

        summary_path = self._resolve_summary_path(evidence_ref.summary_ref)
        summary = self._load_summary(summary_path)
        if summary is None:
            return None

        if is_artifact_stale([summary_path], self.settings.repo_root):
            summary = self._overlay_status(summary, StageStatus.STALE)
            evidence_ref = evidence_ref.model_copy(update={"overall_status": StageStatus.STALE})

        return TrustCurrentResponse(app_version=app_version, evidence_ref=evidence_ref, summary=summary)

    def get_bundle(self, bundle_id: str) -> TrustBundleResponse | None:
        bundle_dir = self.settings.artifacts_dir / "bundles" / bundle_id
        manifest_path = bundle_dir / "manifest.json"
        manifest = read_json(manifest_path, default={})
        if not isinstance(manifest, dict):
            return None

        summary_ref = manifest.get("summary_artifact", "summary.json")
        summary_path = bundle_dir / summary_ref
        summary = self._load_summary(summary_path)
        if summary is None:
            return None

        if is_artifact_stale([summary_path, manifest_path], self.settings.repo_root):
            summary = self._overlay_status(summary, StageStatus.STALE)
        return TrustBundleResponse(bundle_id=bundle_id, summary=summary)

    def _load_file_evidence_ref(self, app_version: str) -> EvidenceRef | None:
        candidates = [
            self.settings.artifacts_dir / "evidence_refs" / f"{app_version}.json",
            self.settings.artifacts_dir / "evidence_refs" / "current.json",
        ]
        for candidate in candidates:
            payload = read_json(candidate, default={})
            if isinstance(payload, dict):
                try:
                    evidence_ref = EvidenceRef.model_validate(payload)
                except Exception:
                    continue
                if evidence_ref.app_version == app_version:
                    return evidence_ref
        return None

    def _build_latest_evidence_ref(self, app_version: str) -> EvidenceRef | None:
        latest = resolve_latest_bundle(self.settings.artifacts_dir)
        if not isinstance(latest, dict):
            return None

        summary_value = latest.get("summary_path")
        bundle_id = latest.get("bundle_id")
        if not isinstance(summary_value, str) or not isinstance(bundle_id, str):
            return None

        summary_path = self._resolve_summary_path(summary_value)
        summary = self._load_summary(summary_path)
        if summary is None:
            return None

        return EvidenceRef(
            app_version=app_version,
            bundle_id=bundle_id,
            summary_ref=self._relative_to_repo(summary_path),
            overall_status=summary.overall_status,
            generated_at=summary.generated_at,
        )

    def _load_summary(self, summary_path: Path) -> EvidenceSummary | None:
        payload = read_json(summary_path, default={})
        if not isinstance(payload, dict):
            return None
        try:
            return EvidenceSummary.model_validate(payload)
        except Exception:
            return None

    def _resolve_summary_path(self, summary_ref: str) -> Path:
        candidate = Path(summary_ref)
        if candidate.is_absolute():
            return candidate
        return (self.settings.repo_root / candidate).resolve()

    def _relative_to_repo(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.settings.repo_root))
        except ValueError:
            return str(path)

    @staticmethod
    def _overlay_status(summary: EvidenceSummary, status: StageStatus) -> EvidenceSummary:
        trust_label = "Evidence stale" if status == StageStatus.STALE else "Verification insufficient"
        note = (
            "This summary was generated before the current repo state. Re-run release validation before using it as sign-off."
            if status == StageStatus.STALE
            else "This summary is incomplete or invalid. Re-run release validation before relying on it."
        )
        highlights = [note, *summary.highlights]
        deduped_highlights = list(dict.fromkeys(highlights))
        return summary.model_copy(
            update={
                "overall_status": status,
                "status": status,
                "trust_label": trust_label,
                "highlights": deduped_highlights,
            }
        )
