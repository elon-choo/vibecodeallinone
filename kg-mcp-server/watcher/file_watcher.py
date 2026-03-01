"""
File System Watcher (Phase 7.3 → 8.1 Multi-Project)
=====================================================
파일 변경을 감지하여 자동으로 Neo4j 지식그래프를 업데이트.
watchdog 라이브러리 기반.

Phase 8.1: 여러 프로젝트 동시 감시 지원
  - ~/.claude/kg-watched-projects.json 설정 파일
  - add_project / remove_project 동적 관리
  - 파일 경로 기반 namespace 자동 결정

사용법:
  python -m mcp_server.watcher.file_watcher --dir /path/to/watch
  python -m mcp_server.watcher.file_watcher --add /path/to/project
  python -m mcp_server.watcher.file_watcher --list
  또는
  python scripts/start_watcher.py --dir /path/to/watch

완료 기준:
  1. 파일 변경 시 1-2초 내 Neo4j 자동 업데이트
  2. debounce 동작 (1초 내 연속 변경 -> 1회만 처리)
  3. 삭제 감지 시 노드 아카이브
  4. PM2로 관리 가능
  5. 여러 프로젝트 동시 감시
"""
import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
from typing import Set, Dict, List, Optional, Tuple
from collections import defaultdict

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileModifiedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileMovedEvent,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  감시 대상 / 제외 패턴
# ──────────────────────────────────────────────
WATCHED_EXTENSIONS: Set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
}

EXCLUDE_DIRS: Set[str] = {
    "node_modules", "__pycache__", ".git", "dist", "build",
    ".next", ".nuxt", "venv", ".venv", "env", ".env",
    ".idea", ".vscode", "coverage", ".pytest_cache",
    ".mypy_cache", ".tox", "egg-info",
}

EXCLUDE_FILES: Set[str] = {
    ".DS_Store", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
}


# ──────────────────────────────────────────────
#  Debounced Handler
# ──────────────────────────────────────────────
class DebouncedHandler(FileSystemEventHandler):
    """Debounce 적용된 파일 이벤트 핸들러.

    동일 파일의 연속 변경(debounce_seconds 이내)은 마지막 1건만 처리.
    """

    def __init__(self, sync_callback, debounce_seconds: float = 1.0):
        super().__init__()
        self.sync_callback = sync_callback
        self.debounce_seconds = debounce_seconds
        # path -> (last_event_time, event_type)
        self._pending: Dict[str, Tuple[float, str]] = {}
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._stats: Dict[str, int] = {
            "created": 0,
            "modified": 0,
            "deleted": 0,
            "moved": 0,
            "synced": 0,
            "errors": 0,
        }

    # ── 필터링 ──────────────────────────────
    def _should_process(self, path: str) -> bool:
        """처리 대상 파일인지 확인"""
        p = Path(path)

        # 확장자 체크
        if p.suffix not in WATCHED_EXTENSIONS:
            return False

        # 제외 디렉토리 체크
        for part in p.parts:
            if part in EXCLUDE_DIRS:
                return False

        # 제외 파일 체크
        if p.name in EXCLUDE_FILES:
            return False

        return True

    # ── watchdog 이벤트 핸들러 ────────────────
    def on_modified(self, event):
        if event.is_directory or not self._should_process(event.src_path):
            return
        self._schedule(event.src_path, "modified")

    def on_created(self, event):
        if event.is_directory or not self._should_process(event.src_path):
            return
        self._schedule(event.src_path, "created")

    def on_deleted(self, event):
        if event.is_directory or not self._should_process(event.src_path):
            return
        self._schedule(event.src_path, "deleted")

    def on_moved(self, event):
        if event.is_directory:
            return
        # 이동 = 이전 경로 삭제 + 새 경로 생성
        if self._should_process(event.src_path):
            self._schedule(event.src_path, "deleted")
        if self._should_process(event.dest_path):
            self._schedule(event.dest_path, "created")

    # ── debounce 스케줄링 ────────────────────
    def _schedule(self, path: str, event_type: str):
        """이벤트 스케줄링 (debounce)"""
        with self._lock:
            self._pending[path] = (time.time(), event_type)
            self._stats[event_type] = self._stats.get(event_type, 0) + 1

        # 기존 타이머 취소 후 재설정
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self.debounce_seconds, self._flush)
        self._timer.daemon = True
        self._timer.start()

    def _flush(self):
        """debounce 시간 경과 후 실제 처리"""
        with self._lock:
            pending = dict(self._pending)
            self._pending.clear()

        for path, (timestamp, event_type) in pending.items():
            try:
                if event_type == "deleted":
                    self._handle_delete(path)
                else:
                    self._handle_sync(path)
                self._stats["synced"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Sync failed for {path}: {e}", exc_info=True)

    def _handle_sync(self, path: str):
        """파일 동기화"""
        logger.info(f"Auto-syncing: {path}")
        self.sync_callback(path)

    def _handle_delete(self, path: str):
        """파일 삭제 처리 -- 관련 노드를 아카이브"""
        logger.info(f"File deleted, archiving nodes: {path}")
        self.sync_callback(path, deleted=True)

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._stats)


# ──────────────────────────────────────────────
#  KGFileWatcher
# ──────────────────────────────────────────────
DEFAULT_EXCLUDE_PATTERNS: List[str] = [
    "node_modules", "__pycache__", ".git", "dist", "build", ".next", "venv",
]

CONFIG_PATH = os.path.expanduser("~/.claude/kg-watched-projects.json")


class KGFileWatcher:
    """지식그래프 파일 감시자 (Multi-Project).

    watch_dirs 내부의 소스 파일(.py/.js/.ts/.jsx/.tsx) 변경을
    실시간으로 감지하여 Neo4j 그래프에 반영한다.

    Phase 8.1: 여러 프로젝트 동시 감시, 설정 파일 기반 관리.
    """

    def __init__(
        self,
        watch_dirs: list,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password123",
        debounce_seconds: float = 1.0,
    ):
        self.watch_dirs = [os.path.abspath(d) for d in watch_dirs]
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.debounce_seconds = debounce_seconds
        self.driver = None
        self.write_back = None
        self.observer: Optional[Observer] = None
        self.handler: Optional[DebouncedHandler] = None

        # Phase 8.1: Multi-project config
        self.config_path = CONFIG_PATH
        self.watched_projects = self._load_config()

    # ── 설정 파일 관리 (Phase 8.1) ───────────────
    def _load_config(self) -> dict:
        """~/.claude/kg-watched-projects.json 로드."""
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Config load failed ({self.config_path}): {e}, using defaults")
        return {
            "projects": [],
            "auto_detect": True,
            "exclude_patterns": list(DEFAULT_EXCLUDE_PATTERNS),
        }

    def _save_config(self):
        """설정을 JSON 파일로 저장."""
        config_dir = os.path.dirname(self.config_path)
        os.makedirs(config_dir, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.watched_projects, f, indent=2, ensure_ascii=False)
        logger.debug(f"Config saved: {self.config_path}")

    def add_project(self, project_path: str) -> dict:
        """프로젝트를 감시 목록에 추가하고 observer에 등록.

        Returns:
            {"added": True/False, "path": ..., "namespace": ...}
        """
        abs_path = os.path.abspath(project_path)

        # 중복 확인
        existing = [p for p in self.watched_projects["projects"] if p["path"] == abs_path]
        if existing:
            logger.info(f"Project already watched: {abs_path}")
            return {"added": False, "path": abs_path, "namespace": existing[0]["namespace"]}

        namespace = Path(abs_path).name
        entry = {"path": abs_path, "enabled": True, "namespace": namespace}
        self.watched_projects["projects"].append(entry)
        self._save_config()

        # 실행 중인 observer가 있으면 즉시 스케줄 추가
        if self.observer is not None and os.path.isdir(abs_path):
            self.observer.schedule(self.handler, abs_path, recursive=True)
            logger.info(f"Added project (live): {abs_path} (ns={namespace})")
        else:
            logger.info(f"Added project (config): {abs_path} (ns={namespace})")

        return {"added": True, "path": abs_path, "namespace": namespace}

    def remove_project(self, project_path: str) -> dict:
        """프로젝트를 감시 목록에서 제거.

        Note: watchdog Observer는 개별 watch 해제를 직접 지원하지 않으므로
        config에서만 제거하고, 다음 재시작 시 반영됨.

        Returns:
            {"removed": True/False, "path": ...}
        """
        abs_path = os.path.abspath(project_path)
        before_count = len(self.watched_projects["projects"])
        self.watched_projects["projects"] = [
            p for p in self.watched_projects["projects"] if p["path"] != abs_path
        ]
        removed = len(self.watched_projects["projects"]) < before_count

        if removed:
            self._save_config()
            logger.info(f"Removed project: {abs_path} (effective after restart)")
        else:
            logger.warning(f"Project not found in config: {abs_path}")

        return {"removed": removed, "path": abs_path}

    def list_projects(self) -> List[dict]:
        """감시 중인 프로젝트 목록 반환."""
        return list(self.watched_projects.get("projects", []))

    def _get_namespace_for_path(self, file_path: str) -> str:
        """파일 경로에서 해당 프로젝트의 namespace를 결정.

        config의 projects를 순회하며 가장 긴 prefix 매치를 반환.
        매치가 없으면 상위 디렉토리 이름을 사용.
        """
        file_path = os.path.abspath(file_path)
        best_match = ""
        best_ns = ""

        for proj in self.watched_projects.get("projects", []):
            proj_path = proj["path"]
            if file_path.startswith(proj_path) and len(proj_path) > len(best_match):
                best_match = proj_path
                best_ns = proj.get("namespace", Path(proj_path).name)

        if best_ns:
            return best_ns

        # fallback: watch_dirs에서 매치
        for wd in self.watch_dirs:
            if file_path.startswith(wd):
                return Path(wd).name

        # 최종 fallback
        parts = Path(file_path).parts
        return parts[-2] if len(parts) > 1 else "unknown"

    def _collect_all_watch_dirs(self) -> List[str]:
        """config + CLI watch_dirs + CLAUDE_PROJECT_DIR 를 합쳐 중복 제거."""
        dirs_set: Dict[str, bool] = {}  # path -> True (순서 유지용)

        # 1) config의 enabled 프로젝트
        for proj in self.watched_projects.get("projects", []):
            if proj.get("enabled", True) and os.path.isdir(proj["path"]):
                dirs_set[proj["path"]] = True

        # 2) CLI에서 전달된 watch_dirs
        for d in self.watch_dirs:
            if os.path.isdir(d):
                dirs_set[d] = True

        # 3) CLAUDE_PROJECT_DIR 환경변수
        env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        if env_dir:
            abs_env = os.path.abspath(env_dir)
            if os.path.isdir(abs_env):
                dirs_set[abs_env] = True

        return list(dirs_set.keys())

    # ── Neo4j 연결 ────────────────────────────
    def _connect(self):
        """Neo4j 연결 및 GraphWriteBack 초기화"""
        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(
            self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
        )
        # 연결 검증
        self.driver.verify_connectivity()

        from mcp_server.pipeline.write_back import GraphWriteBack

        self.write_back = GraphWriteBack(self.driver)
        logger.info(f"Connected to Neo4j at {self.neo4j_uri}")

    # ── 동기화 콜백 ──────────────────────────
    def _sync_callback(self, file_path: str, deleted: bool = False):
        """파일 동기화 콜백 -- DebouncedHandler 에서 호출됨"""
        namespace = self._get_namespace_for_path(file_path)
        if deleted:
            self._archive_deleted(file_path, namespace=namespace)
        else:
            self._sync_file(file_path, namespace=namespace)

    def _sync_file(self, file_path: str, namespace: str = ""):
        """파일 변경/생성 시 그래프 동기화"""
        result = self.write_back.sync_file(file_path)
        if result.get("success"):
            stats = result.get("stats", {})
            logger.info(
                f"Synced [{namespace}] {file_path}: "
                f"{stats.get('functions', 0)} functions, "
                f"{stats.get('classes', 0)} classes"
            )
        else:
            logger.warning(f"Sync returned error [{namespace}] {file_path}: {result.get('error')}")

    def _archive_deleted(self, file_path: str, namespace: str = ""):
        """삭제된 파일의 노드를 아카이브 처리 (archived=true 마킹)"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (n)
                    WHERE n.file_path = $file_path
                       OR n.file_path CONTAINS $basename
                    SET n.archived = true,
                        n.archived_at = datetime()
                    RETURN count(n) AS cnt
                    """,
                    file_path=file_path,
                    basename=os.path.basename(file_path),
                )
                record = result.single()
                cnt = record["cnt"] if record else 0
                logger.info(f"Archived {cnt} nodes for deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Archive failed for {file_path}: {e}", exc_info=True)

    # ── 시작 / 종료 ──────────────────────────
    def start(self):
        """감시 시작 (블로킹).

        config 파일 + CLI watch_dirs + CLAUDE_PROJECT_DIR을 모두 통합하여 감시.
        auto_detect=True이면 CLI/env 디렉토리를 자동으로 config에 추가.
        """
        self._connect()

        self.handler = DebouncedHandler(
            self._sync_callback, debounce_seconds=self.debounce_seconds
        )
        self.observer = Observer()

        # Phase 8.1: 모든 소스에서 watch dirs 수집
        all_dirs = self._collect_all_watch_dirs()

        # auto_detect: CLI/env 디렉토리를 config에 자동 추가
        if self.watched_projects.get("auto_detect", True):
            for d in all_dirs:
                existing = [p for p in self.watched_projects["projects"] if p["path"] == d]
                if not existing:
                    namespace = Path(d).name
                    self.watched_projects["projects"].append(
                        {"path": d, "enabled": True, "namespace": namespace}
                    )
                    logger.info(f"Auto-detected project: {d} (ns={namespace})")
            self._save_config()

        active_count = 0
        for watch_dir in all_dirs:
            ns = self._get_namespace_for_path(watch_dir)
            self.observer.schedule(self.handler, watch_dir, recursive=True)
            logger.info(f"Watching: {watch_dir} (ns={ns})")
            active_count += 1

        if active_count == 0:
            logger.error("No valid watch directories. Exiting.")
            self.stop()
            return

        self.observer.start()
        logger.info(
            f"File watcher started — monitoring {active_count} "
            f"project{'s' if active_count != 1 else ''}"
        )

        try:
            last_synced = 0
            while True:
                time.sleep(10)
                # 주기적 상태 로깅 (변경이 있을 때만)
                stats = self.handler.stats
                if stats["synced"] > last_synced:
                    last_synced = stats["synced"]
                    logger.info(f"Watcher stats: {stats}")
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, shutting down...")
            self.stop()

    def stop(self):
        """감시 중지 및 리소스 정리"""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=5)
            logger.info("Observer stopped")
        if self.driver is not None:
            self.driver.close()
            logger.info("Neo4j driver closed")
        logger.info("File watcher stopped")

    # ── 상태 조회 ─────────────────────────────
    def get_stats(self) -> Dict[str, int]:
        """현재 통계 반환"""
        if self.handler is not None:
            return self.handler.stats
        return {}


# ──────────────────────────────────────────────
#  CLI 엔트리포인트
# ──────────────────────────────────────────────
def main():
    """CLI 엔트리포인트.

    사용법:
      python -m mcp_server.watcher.file_watcher --dir /path/to/project
      python -m mcp_server.watcher.file_watcher --dir ./src ./lib -v
      python -m mcp_server.watcher.file_watcher --add /path/to/project
      python -m mcp_server.watcher.file_watcher --remove /path/to/project
      python -m mcp_server.watcher.file_watcher --list
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="KG File Watcher - 파일 변경 감지 -> Neo4j 자동 업데이트 (Multi-Project)"
    )
    parser.add_argument(
        "--dir",
        nargs="+",
        default=[],
        help="감시할 디렉토리 (여러 개 가능)",
    )
    parser.add_argument(
        "--add",
        metavar="PATH",
        help="프로젝트를 감시 목록에 추가",
    )
    parser.add_argument(
        "--remove",
        metavar="PATH",
        help="프로젝트를 감시 목록에서 제거",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_projects",
        help="감시 중인 프로젝트 목록 출력",
    )
    parser.add_argument(
        "--neo4j-uri",
        default="bolt://localhost:7687",
        help="Neo4j bolt URI (기본값: bolt://localhost:7687)",
    )
    parser.add_argument("--neo4j-user", default="neo4j", help="Neo4j 사용자명")
    parser.add_argument("--neo4j-password", default="password123", help="Neo4j 비밀번호")
    parser.add_argument(
        "--debounce",
        type=float,
        default=1.0,
        help="Debounce 시간(초). 기본값: 1.0",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="디버그 로깅 활성화")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # --list: 프로젝트 목록 출력 후 종료
    if args.list_projects:
        watcher = KGFileWatcher(watch_dirs=[])
        projects = watcher.list_projects()
        if not projects:
            print("No watched projects configured.")
            print(f"Config file: {CONFIG_PATH}")
        else:
            print(f"Watched projects ({len(projects)}):")
            print(f"{'─' * 60}")
            for p in projects:
                status = "enabled" if p.get("enabled", True) else "disabled"
                exists = "OK" if os.path.isdir(p["path"]) else "NOT FOUND"
                print(f"  [{status}] {p['path']}")
                print(f"           namespace={p.get('namespace', '?')}  dir={exists}")
            print(f"{'─' * 60}")
            print(f"Config: {CONFIG_PATH}")
        return

    # --add: 프로젝트 추가 후 종료
    if args.add:
        watcher = KGFileWatcher(watch_dirs=[])
        result = watcher.add_project(args.add)
        if result["added"]:
            print(f"Added: {result['path']} (namespace={result['namespace']})")
        else:
            print(f"Already exists: {result['path']} (namespace={result['namespace']})")
        return

    # --remove: 프로젝트 제거 후 종료
    if args.remove:
        watcher = KGFileWatcher(watch_dirs=[])
        result = watcher.remove_project(args.remove)
        if result["removed"]:
            print(f"Removed: {result['path']}")
        else:
            print(f"Not found in config: {result['path']}")
        return

    # 기본: 감시 모드
    watch_dirs = args.dir if args.dir else ["."]
    watcher = KGFileWatcher(
        watch_dirs=watch_dirs,
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        debounce_seconds=args.debounce,
    )
    watcher.start()


if __name__ == "__main__":
    main()
