#!/usr/bin/env python3
"""
KG Auto-Judge Hook (Phase 8.6)
================================
PostToolUse hook: Write/Edit 도구 사용 후 자동 코드 품질 평가.
Gemini Flash로 평가 -> weight_learner에 자동 피드백.

트리거: Write, Edit 도구 사용 후
조건: .py/.js/.ts 파일, 100 bytes 이상, 5분 debounce
출력: ~/.claude/kg-judge-log/judge.jsonl
"""
import sys
import os
import json
import time
import logging
from pathlib import Path

# ── 로그 설정 ──────────────────────────────────────────────────
LOG_DIR = os.path.expanduser("~/.claude/kg-judge-log")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "judge.jsonl")
DEBOUNCE_FILE = os.path.join(LOG_DIR, "last_judged.json")
DEBOUNCE_SECONDS = 300  # 5분

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "hook.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("kg-auto-judge")

# ── 평가 대상 확장자 ──────────────────────────────────────────
JUDGE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx'}

# ── 최소 파일 크기 (bytes) ────────────────────────────────────
MIN_FILE_SIZE = 100


def main():
    try:
        # stdin에서 hook 데이터 읽기 (Claude Code PostToolUse 표준)
        raw = ""
        try:
            if not sys.stdin.isatty():
                raw = sys.stdin.read()
        except Exception:
            pass

        if not raw:
            # 폴백: 환경변수 (수동 테스트용)
            raw = os.environ.get("CLAUDE_TOOL_INPUT", "")

        if not raw:
            return

        data = json.loads(raw)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})

        # Write 또는 Edit 도구만 처리
        if tool_name not in ("Write", "Edit"):
            return

        # 파일 경로 추출
        file_path = tool_input.get("file_path", "")
        if not file_path:
            return

        # 확장자 확인
        ext = Path(file_path).suffix.lower()
        if ext not in JUDGE_EXTENSIONS:
            logger.debug(f"Skipped (ext={ext}): {file_path}")
            return

        # 파일 존재 및 크기 확인
        if not os.path.isfile(file_path):
            logger.debug(f"Skipped (not found): {file_path}")
            return

        file_size = os.path.getsize(file_path)
        if file_size < MIN_FILE_SIZE:
            logger.debug(f"Skipped (size={file_size}): {file_path}")
            return

        # Debounce: 5분 이내 같은 파일이면 skip
        if _is_debounced(file_path):
            logger.info(f"Debounced: {file_path}")
            return

        # LLM Judge 실행
        logger.info(f"Evaluating: {file_path} (size={file_size})")
        result = _run_judge(file_path)

        if result and result.get("success"):
            score = result.get("overall_score", 3)
            criteria = result.get("criteria", {})
            logger.info(
                f"Score: {score}/5 for {file_path} "
                f"(C={criteria.get('correctness','?')} "
                f"S={criteria.get('security','?')} "
                f"R={criteria.get('readability','?')} "
                f"T={criteria.get('testability','?')})"
            )

            # 결과 로깅
            _log_result(file_path, result)

            # Debounce 기록 업데이트
            _record_debounce(file_path)

            # stderr로 간략 출력 (Claude Code에서 표시됨)
            print(
                f"[KG-Judge] {os.path.basename(file_path)}: "
                f"{score}/5 (C={criteria.get('correctness','?')} "
                f"S={criteria.get('security','?')} "
                f"R={criteria.get('readability','?')} "
                f"T={criteria.get('testability','?')})",
                file=sys.stderr
            )
        else:
            error_msg = result.get("error", "unknown") if result else "no result"
            logger.warning(f"Judge failed for {file_path}: {error_msg}")

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
    except Exception as e:
        logger.error(f"Hook error: {e}", exc_info=True)


def _is_debounced(file_path: str) -> bool:
    """5분 이내 같은 파일 평가했으면 True."""
    try:
        if not os.path.isfile(DEBOUNCE_FILE):
            return False
        with open(DEBOUNCE_FILE, "r") as f:
            records = json.load(f)
        last_time = records.get(file_path, 0)
        return (time.time() - last_time) < DEBOUNCE_SECONDS
    except Exception:
        return False


def _record_debounce(file_path: str):
    """Debounce 기록 저장. 1시간 이상 오래된 기록은 자동 정리."""
    try:
        records = {}
        if os.path.isfile(DEBOUNCE_FILE):
            with open(DEBOUNCE_FILE, "r") as f:
                records = json.load(f)

        records[file_path] = time.time()

        # 1시간 이상 오래된 기록 정리
        now = time.time()
        records = {k: v for k, v in records.items() if now - v < 3600}

        with open(DEBOUNCE_FILE, "w") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        logger.debug(f"Debounce record error: {e}")


def _run_judge(file_path: str) -> dict:
    """LLM Judge를 호출하여 코드 품질 평가. Gemini Flash 사용."""
    try:
        # 프로젝트 경로를 sys.path에 추가
        kg_path = os.getenv("KG_MCP_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if kg_path not in sys.path:
            sys.path.insert(0, kg_path)

        # 환경변수 로드
        from dotenv import load_dotenv
        _env_file = os.path.expanduser("~/.claude/power-pack.env")
        if not os.path.exists(_env_file):
            _env_file = os.path.expanduser("~/.env")
        load_dotenv(_env_file)

        from neo4j import GraphDatabase
        from mcp_server.pipeline.llm_judge import LLMJudge

        password = os.getenv("NEO4J_PASSWORD", "")
        if not password:
            return {"success": False, "error": "NEO4J_PASSWORD not set"}
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), password),
            connection_timeout=5,
        )

        judge = LLMJudge(driver)
        result = judge.evaluate_code(file_path=file_path)

        driver.close()
        return result

    except ImportError as e:
        return {"success": False, "error": f"Import error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _log_result(file_path: str, result: dict):
    """평가 결과를 JSONL 파일에 추가 기록."""
    try:
        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "score": result.get("overall_score"),
            "criteria": result.get("criteria", {}),
            "feedback": result.get("feedback", "")[:200],
            "suggestions": result.get("suggestions", [])[:3],
            "eval_id": result.get("eval_id", ""),
            "truncated": result.get("truncated", False),
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug(f"Log write error: {e}")


if __name__ == "__main__":
    main()
