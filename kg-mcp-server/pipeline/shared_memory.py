"""
Shared Memory Pool (Phase 7.7)
===============================
여러 Claude Code 세션 간 컨텍스트 공유.
Neo4j SharedMemory 노드 기반, 30분 TTL 자동 만료.

MCP 도구: get_shared_context, publish_context
"""
import os
import time
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_TTL_MINUTES = 30


class SharedMemoryPool:
    """세션 간 공유 메모리 풀"""

    def __init__(self, driver):
        self.driver = driver
        self._ensure_constraints()

    def _ensure_constraints(self):
        """SharedMemory 노드 제약 조건 생성"""
        try:
            with self.driver.session() as session:
                session.run("""
                    CREATE CONSTRAINT shared_memory_key IF NOT EXISTS
                    FOR (m:SharedMemory) REQUIRE m.key IS UNIQUE
                """)
        except Exception:
            pass  # 이미 존재

    def publish(self, key: str, value: Any, session_id: str = "",
                project_dir: str = "", ttl_minutes: int = DEFAULT_TTL_MINUTES) -> Dict:
        """컨텍스트를 공유 메모리에 발행.

        Args:
            key: 고유 키 (예: "active_files", "found_bugs", "recent_changes")
            value: 공유할 값 (JSON serializable)
            session_id: 발행한 세션 ID
            project_dir: 프로젝트 디렉토리
            ttl_minutes: 만료 시간 (분)
        """
        try:
            value_json = json.dumps(value, ensure_ascii=False, default=str)

            with self.driver.session() as session:
                session.run("""
                    MERGE (m:SharedMemory {key: $key})
                    SET m.value = $value,
                        m.session_id = $session_id,
                        m.project_dir = $project_dir,
                        m.published_at = datetime(),
                        m.expires_at = datetime() + duration({minutes: $ttl}),
                        m.ttl_minutes = $ttl
                    RETURN m.key AS key
                """, key=key, value=value_json, session_id=session_id,
                     project_dir=project_dir, ttl=ttl_minutes)

            return {"success": True, "key": key, "ttl_minutes": ttl_minutes}
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return {"success": False, "error": str(e)}

    def get_context(self, project_dir: str = "", keys: List[str] = None) -> Dict:
        """공유 메모리에서 컨텍스트 조회.

        Args:
            project_dir: 프로젝트 디렉토리 필터
            keys: 특정 키만 조회 (None이면 전체)
        """
        try:
            self._cleanup_expired()

            with self.driver.session() as session:
                if keys:
                    result = session.run("""
                        MATCH (m:SharedMemory)
                        WHERE m.key IN $keys
                        AND (m.project_dir = $project_dir OR m.project_dir = '' OR $project_dir = '')
                        AND m.expires_at > datetime()
                        RETURN m.key AS key, m.value AS value,
                               m.session_id AS session_id,
                               m.published_at AS published_at,
                               m.ttl_minutes AS ttl
                        ORDER BY m.published_at DESC
                    """, keys=keys, project_dir=project_dir)
                else:
                    result = session.run("""
                        MATCH (m:SharedMemory)
                        WHERE (m.project_dir = $project_dir OR m.project_dir = '' OR $project_dir = '')
                        AND m.expires_at > datetime()
                        RETURN m.key AS key, m.value AS value,
                               m.session_id AS session_id,
                               m.published_at AS published_at,
                               m.ttl_minutes AS ttl
                        ORDER BY m.published_at DESC
                    """, project_dir=project_dir)

                entries = []
                for r in result:
                    entry = dict(r)
                    # JSON 역직렬화
                    try:
                        entry["value"] = json.loads(entry["value"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                    if hasattr(entry.get("published_at"), "isoformat"):
                        entry["published_at"] = entry["published_at"].isoformat()
                    entries.append(entry)

                # 작업 파일 충돌 감지
                conflicts = self._detect_conflicts(entries)

                return {
                    "success": True,
                    "entries": entries,
                    "total": len(entries),
                    "conflicts": conflicts,
                }
        except Exception as e:
            logger.error(f"Get context failed: {e}")
            return {"success": False, "error": str(e)}

    def _detect_conflicts(self, entries: List[Dict]) -> List[Dict]:
        """작업 파일 충돌 감지"""
        conflicts = []
        active_files = {}  # file_path -> session_id

        for entry in entries:
            if entry.get("key", "").startswith("active_file:"):
                file_path = entry["key"].replace("active_file:", "")
                session = entry.get("session_id", "unknown")

                if file_path in active_files and active_files[file_path] != session:
                    conflicts.append({
                        "file": file_path,
                        "sessions": [active_files[file_path], session],
                        "warning": f"File '{file_path}' is being edited by multiple sessions"
                    })
                active_files[file_path] = session

        return conflicts

    def _cleanup_expired(self):
        """만료된 항목 삭제"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:SharedMemory)
                    WHERE m.expires_at < datetime()
                    DELETE m
                    RETURN count(m) AS deleted
                """)
                deleted = result.single()["deleted"]
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired shared memory entries")
        except Exception as e:
            logger.debug(f"Cleanup failed: {e}")

    def delete(self, key: str) -> Dict:
        """특정 키 삭제"""
        try:
            with self.driver.session() as session:
                session.run("MATCH (m:SharedMemory {key: $key}) DELETE m", key=key)
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_active_sessions(self, project_dir: str = "") -> Dict:
        """현재 활성 세션 목록"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:SharedMemory)
                    WHERE m.expires_at > datetime()
                    AND (m.project_dir = $project_dir OR $project_dir = '')
                    WITH DISTINCT m.session_id AS sid,
                         max(m.published_at) AS last_active,
                         count(m) AS entry_count
                    RETURN sid, last_active, entry_count
                    ORDER BY last_active DESC
                """, project_dir=project_dir)
                sessions = [dict(r) for r in result]
                for s in sessions:
                    if hasattr(s.get("last_active"), "isoformat"):
                        s["last_active"] = s["last_active"].isoformat()
                return {"success": True, "sessions": sessions}
        except Exception as e:
            return {"success": False, "error": str(e)}
