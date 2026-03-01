#!/usr/bin/env python3
"""
KG Feedback Collector v3.0 (Phase 1 통합)
==========================================
PostToolUse Hook - Write/Edit 후 자동 피드백 수집

Phase 1 개선사항:
  1-1: Intent-Aware Negative Scoring (Intent별 차등 패널티)
  1-4: Extended Reward Signals (6가지 신호: name/import/call/attr + intent_align + temporal)
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

ANALYTICS_DIR = Path.home() / ".claude" / "mcp-kg-analytics"


def _load_power_pack_env():
    """Load ~/.claude/power-pack.env into os.environ if keys not already set."""
    env_file = Path.home() / ".claude" / "power-pack.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
INJECTED_FILE = ANALYTICS_DIR / "last_injected_identifiers.json"
FEEDBACK_FILE = ANALYTICS_DIR / "feedback_events.jsonl"

# Phase 1-1: Intent별 Negative Scoring 패널티 계수
INTENT_PENALTY = {
    "REFACTOR": 1.5,    # 리팩토링에서 미사용 = 관련 없는 코드 (높은 패널티)
    "DEBUG": 1.2,       # 디버깅에서 미사용 = 에러와 무관
    "TEST": 0.8,        # 테스트에서 미사용 = 참고만 했을 수 있음
    "IMPLEMENT": 0.5,   # 구현에서 미사용 = 영감만 줬을 수 있음
    "DESIGN": 0.3,      # 설계에서 미사용 = 배경 지식
    "DOCUMENT": 0.3,    # 문서화에서 미사용 = 참조용
    "SECURITY": 1.0,    # 보안에서 미사용 = 표준 패널티
}

# Phase 1-4: Intent별 키워드 패턴 (Intent Alignment 신호용)
INTENT_ALIGN_PATTERNS = {
    "REFACTOR": [r"refactor", r"extract", r"rename", r"move", r"clean", r"simplif"],
    "TEST": [r"test", r"assert", r"mock", r"expect", r"describe", r"it\("],
    "DEBUG": [r"fix", r"catch", r"try\s*:", r"except", r"error", r"log"],
    "IMPLEMENT": [r"class\s", r"def\s", r"function\s", r"const\s", r"async\s"],
    "DESIGN": [r"abstract", r"interface", r"pattern", r"layer", r"architect"],
    "SECURITY": [r"auth", r"token", r"encrypt", r"hash", r"sanitize", r"valid"],
    "DOCUMENT": [r"docstring", r'"""', r"comment", r"readme", r"@param", r"@return"],
}


def load_injected():
    """최근 주입된 식별자 + intent + timestamp 로드"""
    try:
        if INJECTED_FILE.exists():
            data = json.loads(INJECTED_FILE.read_text())
            idents = data.get("identifiers", [])
            if idents:
                return {
                    "identifiers": idents,
                    "session_id": data.get("session_id", ""),
                    "intent": data.get("intent", "IMPLEMENT"),
                    "target": data.get("target"),
                    "timestamp": data.get("timestamp", ""),
                    "project_dir": data.get("project_dir", ""),
                }
    except Exception:
        pass
    return None


def get_written_content():
    """PostToolUse hook: stdin JSON에서 tool_input 추출, env var 폴백"""
    tool_input_raw = ""
    # 1차: stdin에서 읽기 (Claude Code PostToolUse hook 표준)
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data:
                parsed = json.loads(stdin_data)
                tool_input_obj = parsed.get("tool_input", {})
                if isinstance(tool_input_obj, dict):
                    content = tool_input_obj.get("content", "") or tool_input_obj.get("new_string", "")
                    file_path = tool_input_obj.get("file_path", "")
                    if content or file_path:
                        return content, file_path
                tool_input_raw = json.dumps(tool_input_obj) if isinstance(tool_input_obj, dict) else str(tool_input_obj)
    except Exception:
        pass
    # 2차: 환경변수 폴백 (수동 테스트용)
    if not tool_input_raw:
        tool_input_raw = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if not tool_input_raw:
        return "", ""
    try:
        data = json.loads(tool_input_raw)
        content = data.get("content", "") or data.get("new_string", "")
        file_path = data.get("file_path", "")
        return content, file_path
    except Exception:
        return tool_input_raw, ""


def check_usage_v3(content: str, identifiers: list, intent: str, inject_time: str) -> tuple:
    """v3: 6가지 신호 기반 분석 (Phase 1-4)

    신호:
    1. name_match (1.0) - 이름 포함
    2. import_match (1.5) - import문
    3. call_match (2.0) - 함수 호출
    4. attr_match (0.5) - 메서드 접근
    5. intent_align (0.5) - Intent와 코드 패턴 일치
    6. temporal (0~1.0) - 주입 후 빠른 사용일수록 높음
    """
    if not content or not identifiers:
        return [], [], {}

    content_lower = content.lower()
    used, unused = [], []
    details = {}

    # Phase 1-4: Intent Alignment 계산
    align_patterns = INTENT_ALIGN_PATTERNS.get(intent, [])
    intent_aligned = any(re.search(p, content_lower) for p in align_patterns)

    # Phase 1-4: Temporal Proximity 계산
    temporal_score = 0.0
    if inject_time:
        try:
            inject_dt = datetime.fromisoformat(inject_time.replace("Z", "+00:00")).replace(tzinfo=None)
            elapsed = (datetime.utcnow() - inject_dt).total_seconds()
            temporal_score = max(0.0, 1.0 - elapsed / 300)  # 5분 이내 = 높은 가중치
        except Exception:
            pass

    for ident in identifiers:
        il = ident.lower()
        esc = re.escape(il)

        signals = {
            "name": bool(re.search(rf'\b{esc}\b', content_lower)),
            "import": bool(re.search(rf'(?:from|import)\s+\S*{esc}', content_lower)),
            "call": bool(re.search(rf'{esc}\s*\(', content_lower)),
            "attr": bool(re.search(rf'{esc}\.', content_lower)),
            "intent_align": intent_aligned,
            "temporal": temporal_score > 0.3,
        }
        weight = (
            signals["name"] * 1.0 +
            signals["import"] * 1.5 +
            signals["call"] * 2.0 +
            signals["attr"] * 0.5 +
            signals["intent_align"] * 0.5 +
            temporal_score * 0.5
        )
        details[ident] = {"signals": signals, "weight": round(weight, 1)}

        # 최소 name/import/call/attr 중 하나는 매칭되어야 "used"
        has_code_signal = signals["name"] or signals["import"] or signals["call"] or signals["attr"]
        if has_code_signal and weight >= 1.0:
            used.append(ident)
        else:
            unused.append(ident)

    return used, unused, details


def record(session_id: str, used: list, unused: list, file_path: str,
           intent: str, details: dict):
    """피드백 이벤트 기록 (Intent 정보 포함)"""
    try:
        total = len(used) + len(unused)
        rate = round(len(used) / total * 100, 1) if total > 0 else 0
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "context_feedback",
            "session_id": session_id,
            "intent": intent,
            "used_identifiers": used,
            "unused_identifiers": unused,
            "used_count": len(used),
            "unused_count": len(unused),
            "usage_rate": rate,
            "file_path": file_path,
            "details": {k: v["weight"] for k, v in details.items()},
        }
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def update_neo4j(used: list, unused: list, details: dict, intent: str):
    """v3: Dual Score + Intent-Aware Negative + Multi-Signal"""
    try:
        from neo4j import GraphDatabase
        _load_power_pack_env()
        password = os.getenv("NEO4J_PASSWORD", "")
        if not password:
            return
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), password),
            connection_timeout=2,
        )
        with driver.session() as session:
            # 유용한 노드: positive_score += 신호별 가중치
            if used:
                for name in used:
                    weight = 1.0
                    if details and name in details:
                        weight = max(details[name].get("weight", 1.0), 1.0)
                    session.run("""
                        MATCH (n) WHERE n.name = $name
                        SET n.positive_score = coalesce(n.positive_score, 0) + $weight,
                            n.useful_count = coalesce(n.useful_count, 0) + 1,
                            n.last_useful = datetime(),
                            n.last_intent_hit = $intent,
                            n.relevance_score =
                                (coalesce(n.positive_score, 0) + $weight - 0.5 * coalesce(n.negative_score, 0))
                                / (coalesce(n.positive_score, 0) + $weight + coalesce(n.negative_score, 0) + 1.0)
                    """, name=name, weight=weight, intent=intent)

            # Phase 1-1: Intent-Aware Negative Scoring
            if unused:
                penalty = INTENT_PENALTY.get(intent, 1.0)
                for name in unused:
                    session.run("""
                        MATCH (n) WHERE n.name = $name
                        SET n.negative_score = coalesce(n.negative_score, 0) + $penalty,
                            n.unused_count = coalesce(n.unused_count, 0) + 1,
                            n.last_intent_miss = $intent,
                            n.relevance_score =
                                (coalesce(n.positive_score, 0) - 0.5 * (coalesce(n.negative_score, 0) + $penalty))
                                / (coalesce(n.positive_score, 0) + coalesce(n.negative_score, 0) + $penalty + 1.0)
                    """, name=name, penalty=penalty, intent=intent)

            # Phase 2-2: Edge 가중치 피드백 (함께 사용된 노드 쌍)
            if len(used) >= 2:
                for i in range(len(used)):
                    for j in range(i + 1, min(len(used), i + 4)):  # 최대 3쌍
                        session.run("""
                            MATCH (a) WHERE a.name = $name_a
                            MATCH (b) WHERE b.name = $name_b
                            MERGE (a)-[r:CO_USED]->(b)
                            SET r.count = coalesce(r.count, 0) + 1,
                                r.last_used = datetime(),
                                r.intent = $intent
                        """, name_a=used[i], name_b=used[j], intent=intent)

        driver.close()
    except Exception:
        pass


def main():
    injected = load_injected()
    if not injected:
        sys.exit(0)

    identifiers = injected["identifiers"]
    session_id = injected["session_id"]
    intent = injected["intent"]
    inject_time = injected["timestamp"]

    content, file_path = get_written_content()
    if not content:
        sys.exit(0)

    # 크로스 세션 오염 방지: 작성 파일이 주입 프로젝트 범위 내인지 확인
    project_dir = injected.get("project_dir", "")
    if project_dir and file_path and not file_path.startswith(project_dir):
        sys.exit(0)

    # 코드 파일만 처리
    code_exts = ['.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.java', '.rs', '.cpp', '.c', '.vue', '.svelte']
    if file_path and not any(file_path.endswith(ext) for ext in code_exts):
        sys.exit(0)

    used, unused, details = check_usage_v3(content, identifiers, intent, inject_time)

    if used or unused:
        record(session_id, used, unused, file_path, intent, details)
        update_neo4j(used, unused, details, intent)
        total = len(used) + len(unused)
        penalty = INTENT_PENALTY.get(intent, 1.0)

        # Phase 4: A/B 테스트 결과 기록
        try:
            from ab_test_engine import record_ab_result, assign_strategy, evaluate_and_promote
            strategy = assign_strategy(session_id)
            record_ab_result(session_id, strategy, len(used), len(unused))
            # 평가 시도 (충분한 샘플이 모이면 자동 승자 판정)
            result = evaluate_and_promote()
            if result and result.get("action") in ("promoted", "defended"):
                print(f"[KG-AB] {result['action']}: {result}", file=sys.stderr)
        except Exception:
            pass

        print(f"[KG-Feedback v3] intent={intent} penalty={penalty} used={len(used)} unused={len(unused)} rate={len(used)/total*100:.0f}%", file=sys.stderr)


if __name__ == "__main__":
    main()
