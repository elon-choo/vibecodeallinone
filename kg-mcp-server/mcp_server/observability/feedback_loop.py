#!/usr/bin/env python3
"""
Feedback Loop & Trauma Learning System v1.0
=============================================
Part5-Q9 (피드백 루프) + Part6-Q11 (기억 강화 학습) 구현

작동 원리:
1. Hook이 KG 컨텍스트를 주입 → injected_identifiers 기록
2. AI가 코드를 작성 (Write/Edit)
3. PostToolUse hook이 작성된 코드에서 identifier 사용 여부 확인
4. 사용된 identifier → useful_count +1, Neo4j access_count +1
5. 미사용 identifier → unused_count +1, Neo4j relevance_score decay
6. 시간이 지나면 자주 유용한 노드가 더 높은 순위로 올라감

A-Mem 스타일: 새 피드백이 기존 노드의 가중치를 업데이트하여
지식 그래프가 지속적으로 자기 개선 (Self-Improving)
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

ANALYTICS_DIR = Path.home() / ".claude" / "mcp-kg-analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_FILE = ANALYTICS_DIR / "feedback_events.jsonl"
INJECTED_CONTEXT_FILE = ANALYTICS_DIR / "last_injected_identifiers.json"

# ═══════════════════════════════════════════════════════════════════════════
# 1. 주입된 컨텍스트 식별자 추적
# ═══════════════════════════════════════════════════════════════════════════

def save_injected_identifiers(identifiers: List[str], session_id: str = ""):
    """Hook이 주입한 KG 컨텍스트의 식별자 목록을 저장"""
    try:
        data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "identifiers": identifiers,
        }
        with open(INJECTED_CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to save injected identifiers: {e}")


def load_injected_identifiers() -> dict:
    """가장 최근에 주입된 식별자 목록 로드"""
    try:
        if INJECTED_CONTEXT_FILE.exists():
            return json.loads(INJECTED_CONTEXT_FILE.read_text())
    except Exception:
        pass
    return {"identifiers": [], "session_id": "", "timestamp": ""}


# ═══════════════════════════════════════════════════════════════════════════
# 2. 피드백 수집: 코드에서 식별자 사용 여부 확인
# ═══════════════════════════════════════════════════════════════════════════

def analyze_code_for_identifiers(code_content: str, identifiers: List[str]) -> dict:
    """v2: 다중 신호 기반 식별자 사용 분석 (논문 #11, #12, #17 기반)

    신호별 가중치:
    - name_match (이름 포함): 1.0
    - import_match (import문): 1.5
    - call_match (함수 호출): 2.0
    - attribute_match (메서드 접근): 0.5
    """
    if not code_content or not identifiers:
        return {"used": [], "unused": [], "usage_rate": 0.0, "details": {}}

    code_lower = code_content.lower()
    used = []
    unused = []
    details = {}

    for ident in identifiers:
        il = ident.lower()
        esc = re.escape(il)

        signals = {
            "name_match": bool(re.search(rf'\b{esc}\b', code_lower)),
            "import_match": bool(re.search(rf'(?:from|import)\s+\S*{esc}', code_lower)),
            "call_match": bool(re.search(rf'{esc}\s*\(', code_lower)),
            "attribute_match": bool(re.search(rf'{esc}\s*\.', code_lower)),
        }

        weight = (
            signals["name_match"] * 1.0 +
            signals["import_match"] * 1.5 +
            signals["call_match"] * 2.0 +
            signals["attribute_match"] * 0.5
        )

        details[ident] = {"signals": signals, "weight": round(weight, 1)}

        if weight > 0:
            used.append(ident)
        else:
            unused.append(ident)

    total = len(identifiers)
    usage_rate = len(used) / total * 100 if total > 0 else 0.0

    return {
        "used": used,
        "unused": unused,
        "usage_rate": round(usage_rate, 1),
        "details": details,
    }


def record_feedback(session_id: str, used: List[str], unused: List[str],
                    file_path: str = "", feedback_type: str = "auto"):
    """피드백 이벤트를 기록"""
    try:
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "context_feedback",
            "session_id": session_id,
            "feedback_type": feedback_type,  # auto / explicit_positive / explicit_negative
            "used_identifiers": used,
            "unused_identifiers": unused,
            "used_count": len(used),
            "unused_count": len(unused),
            "usage_rate": round(len(used) / max(len(used) + len(unused), 1) * 100, 1),
            "file_path": file_path,
        }
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to record feedback: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 3. 트라우마 학습: Neo4j 노드 가중치 업데이트
# ═══════════════════════════════════════════════════════════════════════════

def update_node_weights(driver, used: List[str], unused: List[str],
                        details: dict = None):
    """v2: Dual Score + 다중 신호 가중치 기반 Neo4j 노드 업데이트

    논문 기반 개선 (#5 Dual Feedback, #16 Time-Decay, #20 Multi-Reward):
    - positive_score / negative_score 분리 관리
    - 신호별 가중치 차등 적용 (import > call > name)
    - relevance_score = Wilson Score 변형으로 정규화
    - last_useful 기록 (시간 감쇠용)
    """
    if not driver:
        return

    try:
        with driver.session() as session:
            # 유용했던 노드: positive_score 증가 (신호별 가중치)
            if used:
                for name in used:
                    weight = 1.0
                    if details and name in details:
                        weight = max(details[name].get("weight", 1.0), 1.0)

                    session.run("""
                        MATCH (n) WHERE n.name = $name
                        SET n.access_count = coalesce(n.access_count, 0) + 1,
                            n.positive_score = coalesce(n.positive_score, 0) + $weight,
                            n.useful_count = coalesce(n.useful_count, 0) + 1,
                            n.last_useful = datetime(),
                            n.relevance_score =
                                (coalesce(n.positive_score, 0) + $weight
                                 - 0.5 * coalesce(n.negative_score, 0))
                                / (coalesce(n.positive_score, 0) + $weight
                                   + coalesce(n.negative_score, 0) + 1.0)
                    """, name=name, weight=weight)

            # 미사용 노드: negative_score 증가 (트라우마)
            if unused:
                session.run("""
                    UNWIND $names AS name
                    MATCH (n) WHERE n.name = name
                    SET n.negative_score = coalesce(n.negative_score, 0) + 1,
                        n.unused_count = coalesce(n.unused_count, 0) + 1,
                        n.relevance_score =
                            (coalesce(n.positive_score, 0)
                             - 0.5 * (coalesce(n.negative_score, 0) + 1))
                            / (coalesce(n.positive_score, 0)
                               + coalesce(n.negative_score, 0) + 2.0)
                """, names=unused)

    except Exception as e:
        logger.warning(f"Failed to update node weights: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 4. PostToolUse에서 호출되는 메인 함수
# ═══════════════════════════════════════════════════════════════════════════

def process_write_feedback(written_content: str, file_path: str = ""):
    """Write/Edit 후 호출: 주입된 컨텍스트의 유효성을 측정하고 가중치 업데이트

    흐름:
    1. 최근 주입된 식별자 로드
    2. 작성된 코드에서 사용 여부 분석
    3. 피드백 이벤트 기록
    4. Neo4j 노드 가중치 업데이트
    """
    # 주입된 식별자 로드
    injected = load_injected_identifiers()
    identifiers = injected.get("identifiers", [])
    session_id = injected.get("session_id", "unknown")

    if not identifiers:
        return  # 주입된 컨텍스트가 없으면 스킵

    # 코드에서 사용 여부 분석
    analysis = analyze_code_for_identifiers(written_content, identifiers)

    # 피드백 기록
    record_feedback(
        session_id=session_id,
        used=analysis["used"],
        unused=analysis["unused"],
        file_path=file_path,
        feedback_type="auto",
    )

    # Neo4j 가중치 업데이트 (v2: dual score + multi-signal)
    try:
        from neo4j import GraphDatabase
        password = os.getenv("NEO4J_PASSWORD", "")
        if not password:
            logger.debug("Neo4j weight update skipped: NEO4J_PASSWORD not set")
            return analysis
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), password),
            connection_timeout=2,
        )
        update_node_weights(driver, analysis["used"], analysis["unused"],
                            details=analysis.get("details"))
        driver.close()
    except Exception as e:
        logger.debug(f"Neo4j weight update skipped: {e}")

    return analysis


# ═══════════════════════════════════════════════════════════════════════════
# 5. 피드백 통계 조회 (대시보드용)
# ═══════════════════════════════════════════════════════════════════════════

def get_feedback_stats(days: int = 7) -> dict:
    """피드백 통계 조회"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    events = []

    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        e = json.loads(line.strip())
                        ts = e.get("timestamp", "").replace("Z", "+00:00")
                        t = datetime.fromisoformat(ts).replace(tzinfo=None)
                        if t > cutoff:
                            events.append(e)
                    except Exception:
                        continue
        except Exception:
            pass

    if not events:
        return {
            "total_feedbacks": 0,
            "avg_usage_rate": None,
            "total_used": 0,
            "total_unused": 0,
            "top_useful": [],
            "top_unused": [],
        }

    total_used = sum(e.get("used_count", 0) for e in events)
    total_unused = sum(e.get("unused_count", 0) for e in events)
    avg_rate = sum(e.get("usage_rate", 0) for e in events) / len(events)

    # 가장 자주 유용했던/미사용된 식별자
    from collections import Counter
    used_counter = Counter()
    unused_counter = Counter()
    for e in events:
        used_counter.update(e.get("used_identifiers", []))
        unused_counter.update(e.get("unused_identifiers", []))

    return {
        "total_feedbacks": len(events),
        "avg_usage_rate": round(avg_rate, 1),
        "total_used": total_used,
        "total_unused": total_unused,
        "top_useful": [{"name": n, "count": c} for n, c in used_counter.most_common(5)],
        "top_unused": [{"name": n, "count": c} for n, c in unused_counter.most_common(5)],
    }
