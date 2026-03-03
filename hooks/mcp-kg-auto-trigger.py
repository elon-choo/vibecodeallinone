#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Knowledge Graph Auto-Trigger Hook v4.0 (Agentic)
=====================================================
Intent-Aware Context Selection:
  프롬프트 → Intent 분류 → 타겟 추출 → Intent별 Neo4j 쿼리 전략 → 랭킹 → 주입

v3→v4 변경점:
- Intent Router: REFACTOR/TEST/DEBUG/DESIGN/SECURITY/DOCUMENT/IMPLEMENT 7가지 의도 분류
- Target Extraction: 프롬프트에서 대상 함수/클래스명 정확 추출
- Strategy-based Query: Intent별로 다른 Cypher 쿼리 (호출관계, 시그니처, 패턴 등)
- access_count 가중치: 자주 참조된 노드 우선
"""

import os
import sys
import json
import re
import uuid
from typing import List, Tuple, Optional
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════

KEYWORD_WEIGHTS = {
    "함수": 3, "function": 3, "클래스": 3, "class": 3, "메서드": 3, "method": 3,
    "버그": 3, "bug": 3, "에러": 3, "디버그": 3, "debug": 3,
    "리팩토링": 3, "refactor": 3, "구현": 3, "implement": 3,
    "아키텍처": 3, "architecture": 3, "컴포넌트": 3, "component": 3,
    "api": 3, "endpoint": 3, "스키마": 3, "schema": 3,
    "import": 3, "패키지": 3, "package": 3,
    "보안": 3, "security": 3, "취약점": 3, "vulnerability": 3,
    "인젝션": 3, "injection": 3, "인증": 3, "auth": 3,
    "배포": 3, "deploy": 3, "마이그레이션": 3, "migration": 3,
    "코드": 2, "code": 2,
    "설계": 2, "design": 2, "패턴": 2, "pattern": 2,
    "모듈": 2, "module": 2, "테스트": 2, "test": 2,
    "최적화": 2, "optimize": 2, "성능": 2, "performance": 2,
    "데이터베이스": 2, "database": 2, "쿼리": 2, "query": 2,
    "타입": 2, "type": 2, "인터페이스": 2, "interface": 2,
    "변수": 2, "variable": 2,
    "수정": 1, "fix": 1, "추가": 1, "add": 1, "생성": 1, "create": 1,
    "확인": 1, "check": 1, "분석": 1, "analyze": 1, "검토": 1, "review": 1,
    "작성": 1, "write": 1, "error": 1, "문제": 1, "issue": 1,
}

DEV_THRESHOLD = 3
CODE_FILE_PATTERNS = [r'\.(py|js|ts|tsx|jsx|go|java|rs|cpp|c|swift|kt|rb|php|vue|svelte)\b']

ANALYTICS_DIR = Path.home() / ".claude" / "mcp-kg-analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
CONTEXT_CACHE_FILE = ANALYTICS_DIR / "last_kg_context.json"

# ═══════════════════════════════════════════════════════════════════════════
# Intent Router (에이전틱 핵심)
# ═══════════════════════════════════════════════════════════════════════════

INTENT_PATTERNS = {
    "REFACTOR": [r"리팩토링", r"refactor", r"개선", r"성능\s*개선", r"optimize", r"최적화", r"클린"],
    "TEST":     [r"테스트", r"test", r"유닛", r"unit", r"mock", r"검증", r"커버리지", r"coverage"],
    "DEBUG":    [r"에러", r"error", r"버그", r"bug", r"오류", r"exception", r"디버그", r"debug", r"fix", r"수정.*오류"],
    "DESIGN":   [r"설계", r"design", r"아키텍처", r"architecture", r"구조", r"structure", r"레이어", r"layer"],
    "SECURITY": [r"보안", r"security", r"취약점", r"vulnerability", r"인젝션", r"injection", r"인증", r"auth", r"XSS", r"CSRF"],
    "DOCUMENT": [r"문서", r"document", r"docstring", r"주석", r"comment", r"설명.*작성", r"README"],
    "IMPLEMENT":[r"구현", r"implement", r"추가", r"add", r"생성", r"create", r"만들어", r"개발"],
}


def classify_intent(prompt: str) -> str:
    """프롬프트에서 작업 의도를 분류. 가장 높은 매칭 점수의 intent 반환."""
    prompt_lower = prompt.lower()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(3 if re.search(p, prompt_lower) else 0 for p in patterns)
        if score > 0:
            scores[intent] = score

    if not scores:
        return "IMPLEMENT"  # 기본값
    return max(scores, key=scores.get)


def extract_target(prompt: str) -> Optional[str]:
    """프롬프트에서 작업 대상 식별자(함수명/클래스명)를 추출."""
    # 패턴 1: "XXX 함수를", "XXX 클래스를", "XXX에 대한"
    m = re.search(r'(\b[a-zA-Z_]\w+(?:_\w+)*)\s*(?:함수|클래스|메서드|모듈)(?:를|을|의|에)', prompt)
    if m:
        return m.group(1)

    # 패턴 1b: "XXX에서", "XXX에 대한"
    m = re.search(r'(\b[a-zA-Z_]\w{2,})\s*(?:에서|에 대한)', prompt)
    if m:
        return m.group(1)

    # 패턴 2: "함수 XXX", "클래스 XXX"
    m = re.search(r'(?:함수|클래스|메서드|모듈)\s+(\b[a-zA-Z_]\w+(?:_\w+)*)', prompt)
    if m:
        return m.group(1)

    # 패턴 3: snake_case 식별자 (가장 구체적인 것)
    snakes = re.findall(r'\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b', prompt)
    if snakes:
        # 가장 긴 것이 보통 가장 구체적
        return max(snakes, key=len)

    # 패턴 4: PascalCase 식별자
    pascals = re.findall(r'\b([A-Z][a-zA-Z0-9]{2,})\b', prompt)
    # 일반 영단어 제외
    stop = {"The","This","That","What","How","For","With","From","About","After","Before",
            "MANDATORY","BEFORE","DEVELOPMENT","Knowledge","Skipping"}
    pascals = [p for p in pascals if p not in stop]
    if pascals:
        return pascals[0]

    # 패턴 5: .py/.ts 파일명에서 모듈명 추출
    m = re.search(r'(\w+)\.(py|ts|js|tsx|jsx)\b', prompt)
    if m:
        return m.group(1)

    return None

# ═══════════════════════════════════════════════════════════════════════════
# Auto-Index New Projects
# ═══════════════════════════════════════════════════════════════════════════

_INDEX_LOCK_DIR = ANALYTICS_DIR / "index_locks"


def _auto_index_if_new_project():
    """새 프로젝트 감지 시 백그라운드 벌크 인덱싱 트리거.
    - Neo4j에 해당 namespace 노드가 0개이면 새 프로젝트
    - lock 파일로 중복 실행 방지 (24시간)
    - 백그라운드로 실행하여 Hook timeout(8초)에 영향 없음
    """
    ns = _get_project_namespace()
    if not ns:
        return

    # lock 파일 확인 (24시간 내 이미 인덱싱 시도함)
    _INDEX_LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = _INDEX_LOCK_DIR / f"{ns}.lock"
    if lock_file.exists():
        try:
            age = (datetime.utcnow() - datetime.utcfromtimestamp(lock_file.stat().st_mtime)).total_seconds()
            if age < 86400:  # 24시간 이내
                return
        except Exception:
            pass

    # Neo4j에 해당 namespace 노드 수 확인
    driver = _get_driver()
    if not driver:
        return
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (n) WHERE n.namespace = $ns RETURN count(n) as cnt",
                ns=ns
            )
            cnt = result.single()["cnt"]
        driver.close()
    except Exception:
        try:
            driver.close()
        except Exception:
            pass
        return

    if cnt > 0:
        # 이미 인덱싱된 프로젝트 → lock 파일 생성하고 스킵
        lock_file.touch()
        return

    # 새 프로젝트! 풀 파이프라인 백그라운드 실행 (index → describe → embed)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir or not os.path.isdir(project_dir):
        return

    # auto_index_project.py (v2 풀 파이프라인) 사용
    kg_root = Path.home() / ".claude" / "kg-mcp-server"
    indexer = kg_root / "scripts" / "auto_index_project.py"
    if not indexer.exists():
        # fallback: 레거시 벌크 인덱서
        indexer = Path.home() / ".claude" / "hooks" / "kg-bulk-indexer.py"
    if not indexer.exists():
        return

    # lock 먼저 생성 (중복 방지)
    lock_file.touch()

    try:
        import subprocess
        log_file = ANALYTICS_DIR / "auto_index.log"
        with open(log_file, "a") as log:
            log.write(f"[{datetime.utcnow().isoformat()}] Auto-indexing new project (full pipeline): {ns} ({project_dir})\n")
        # 백그라운드 실행 (Hook을 블로킹하지 않음)
        subprocess.Popen(
            ["python3", str(indexer), project_dir],
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# Intent-Aware Neo4j Queries
# ═══════════════════════════════════════════════════════════════════════════

def _load_power_pack_env():
    """Load ~/.claude/power-pack.env into os.environ if keys not already set."""
    env_file = Path.home() / ".claude" / "power-pack.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def _get_driver():
    try:
        _load_power_pack_env()
        password = os.getenv("NEO4J_PASSWORD", "")
        if not password:
            return None
        from neo4j import GraphDatabase
        return GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), password),
            connection_timeout=2,
        )
    except Exception:
        return None


def _get_project_namespace() -> str:
    """현재 프로젝트의 namespace 추출 (CLAUDE_PROJECT_DIR 기반)."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return Path(project_dir).name
    return ""


def _build_ns_filter(alias: str = "n") -> str:
    """프로젝트 namespace 필터 Cypher절 생성.
    namespace가 없는 노드(초기 인덱싱)도 현재 프로젝트와 동일하면 포함."""
    ns = _get_project_namespace()
    if not ns:
        return ""
    # 현재 프로젝트 namespace 또는 namespace 미지정(레거시) 노드 포함
    return f" AND ({alias}.namespace IS NULL OR {alias}.namespace = $ns)"


def _try_hybrid_search(query: str, limit: int = 5) -> List[dict]:
    """MCP 서버의 HybridSearchEngine을 직접 호출 (vector search 포함)."""
    try:
        # Auto-detect KG MCP server path
        kg_root = os.getenv("KG_MCP_ROOT", str(Path.home() / ".claude" / "kg-mcp-server"))
        sys.path.insert(0, kg_root)
        # Voyage API key must be set in environment (no hardcoded fallback)
        from mcp_server.pipeline.hybrid_search import HybridSearchEngine
        from mcp_server.pipeline.query_router import QueryRouter

        driver = _get_driver()
        if not driver:
            return []

        hs = HybridSearchEngine(driver)
        qr = QueryRouter()
        strategy = qr.get_search_strategy(query)
        results = hs.search(query, strategy, limit)
        driver.close()

        # 결과를 표준 형식으로 변환
        items = []
        for r in results:
            items.append({
                "name": r.get("name", r.get("qualified_name", "?")),
                "type": r.get("node_type", r.get("type", "Function")),
                "doc": (r.get("docstring", "") or r.get("ai_description", ""))[:200],
                "module": r.get("module", r.get("namespace", "")),
                "score": r.get("score", 0),
            })
        return items
    except Exception as e:
        print(f"[MCP-KG] Hybrid search failed: {e}", file=sys.stderr)
        return []


def query_by_intent(intent: str, target: Optional[str], keywords: List[str], limit: int = 5) -> List[dict]:
    """Intent별 최적화된 검색. hybrid_search 우선, Cypher 폴백."""

    # Phase 10.5: hybrid_search (keyword + vector) 우선 시도
    query_text = target if target else " ".join(keywords[:3])
    if query_text:
        hybrid_items = _try_hybrid_search(query_text, limit)
        if hybrid_items:
            _save_cache(hybrid_items)
            return hybrid_items

    # Fallback: 기존 Cypher 쿼리
    driver = _get_driver()
    if not driver:
        return _load_cache()

    try:
        with driver.session() as session:
            if target:
                items = _query_with_target(session, intent, target, limit)
                if items:
                    driver.close()
                    _save_cache(items)
                    return items

            items = _query_by_keywords(session, keywords, limit)

            if len(items) < 2:
                items.extend(_query_patterns(session, keywords, limit - len(items)))

        driver.close()
        if items:
            _save_cache(items)
        return items
    except Exception as e:
        print(f"[MCP-KG] Neo4j failed ({e}), cache fallback", file=sys.stderr)
        try:
            driver.close()
        except Exception:
            pass  # driver.close() best-effort during error handling
        return _load_cache()


def _query_with_target(session, intent: str, target: str, limit: int) -> List[dict]:
    """타겟이 있을 때 Intent별 그래프 탐색."""

    if intent == "REFACTOR":
        # 대상 + 호출하는/호출받는 함수 (2-hop)
        result = session.run("""
            MATCH (t) WHERE toLower(t.name) = toLower($target)
            OPTIONAL MATCH (t)-[:CALLS]->(out)
            OPTIONAL MATCH (inc)-[:CALLS]->(t)
            WITH t, collect(DISTINCT out)[0..3] AS outs, collect(DISTINCT inc)[0..3] AS incs
            UNWIND ([t] + outs + incs) AS n
            WITH DISTINCT n WHERE n IS NOT NULL
            RETURN n.name AS name, labels(n)[0] AS type,
                   LEFT(COALESCE(n.docstring,''), 120) AS doc,
                   COALESCE(n.module,'') AS module
            LIMIT $limit
        """, target=target, limit=limit)
        return [dict(r) for r in result]

    elif intent == "TEST":
        # 대상 함수의 시그니처 + 같은 모듈의 다른 함수
        result = session.run("""
            MATCH (t) WHERE toLower(t.name) = toLower($target)
            OPTIONAL MATCH (m:Module)-[:DEFINES]->(t)
            OPTIONAL MATCH (m)-[:DEFINES]->(sibling)
            WHERE sibling <> t
            WITH t, collect(DISTINCT sibling)[0..2] AS siblings
            UNWIND ([t] + siblings) AS n
            WITH DISTINCT n WHERE n IS NOT NULL
            RETURN n.name AS name, labels(n)[0] AS type,
                   COALESCE(n.docstring,'') AS doc,
                   COALESCE(n.module,'') AS module,
                   COALESCE(n.args, '') AS args
            LIMIT $limit
        """, target=target, limit=limit)
        return [dict(r) for r in result]

    elif intent == "DEBUG":
        # 대상 + 호출 체인 (에러 전파 경로)
        result = session.run("""
            MATCH (t) WHERE toLower(t.name) = toLower($target)
            OPTIONAL MATCH path = (t)-[:CALLS*1..2]->(dep)
            WITH t, collect(DISTINCT dep)[0..4] AS deps
            UNWIND ([t] + deps) AS n
            WITH DISTINCT n WHERE n IS NOT NULL
            RETURN n.name AS name, labels(n)[0] AS type,
                   LEFT(COALESCE(n.docstring,''), 120) AS doc,
                   COALESCE(n.module,'') AS module
            LIMIT $limit
        """, target=target, limit=limit)
        return [dict(r) for r in result]

    elif intent == "DOCUMENT":
        # 대상 함수의 전체 docstring + args + 호출자 (사용 예시용)
        result = session.run("""
            MATCH (t) WHERE toLower(t.name) = toLower($target)
            OPTIONAL MATCH (caller)-[:CALLS]->(t)
            WITH t, collect(DISTINCT caller.name)[0..3] AS callers
            RETURN t.name AS name, labels(t)[0] AS type,
                   COALESCE(t.docstring,'') AS doc,
                   COALESCE(t.module,'') AS module,
                   COALESCE(t.args,'') AS args,
                   callers
            LIMIT 1
        """, target=target)
        items = []
        for r in result:
            d = dict(r)
            callers = d.pop("callers", [])
            if callers:
                d["doc"] = (d.get("doc","") + f" | 호출자: {', '.join(callers)}")[:200]
            items.append(d)
        return items

    elif intent in ("DESIGN", "SECURITY"):
        # 모듈 수준 구조 + 관련 패턴
        result = session.run("""
            MATCH (t) WHERE toLower(t.name) CONTAINS toLower($target)
            RETURN t.name AS name, labels(t)[0] AS type,
                   LEFT(COALESCE(t.docstring, t.description, ''), 120) AS doc,
                   COALESCE(t.module,'') AS module
            LIMIT $limit
        """, target=target, limit=limit)
        return [dict(r) for r in result]

    else:  # IMPLEMENT
        # 이름 매칭 + 같은 모듈 구조
        result = session.run("""
            MATCH (t) WHERE toLower(t.name) CONTAINS toLower($target)
            RETURN t.name AS name, labels(t)[0] AS type,
                   LEFT(COALESCE(t.docstring,''), 120) AS doc,
                   COALESCE(t.module,'') AS module
            ORDER BY CASE WHEN toLower(t.name) = toLower($target) THEN 0 ELSE 1 END,
                     COALESCE(t.access_count, 0) DESC
            LIMIT $limit
        """, target=target, limit=limit)
        return [dict(r) for r in result]


def _query_by_keywords(session, keywords: List[str], limit: int) -> List[dict]:
    """v3: Dual Score + Adaptive Decay 기반 키워드 쿼리 (Phase 1-2)."""
    ns = _get_project_namespace()
    ns_filter = _build_ns_filter("n")
    result = session.run(f"""
        UNWIND $keywords AS kw
        MATCH (n)
        WHERE (toLower(n.name) CONTAINS toLower(kw)
           OR toLower(COALESCE(n.docstring, '')) CONTAINS toLower(kw)){ns_filter}
        WITH DISTINCT n,
             CASE WHEN any(kw IN $keywords WHERE toLower(n.name) CONTAINS toLower(kw)) THEN 10 ELSE 5 END AS text_score,
             COALESCE(n.access_count, 0) AS access,
             COALESCE(n.relevance_score, 0.5) AS relevance,
             CASE WHEN n.last_useful IS NOT NULL
                 THEN duration.between(n.last_useful, datetime()).days
                 ELSE 90
             END AS days_since,
             CASE
                 WHEN any(kw IN ['util','helper','common','base'] WHERE toLower(COALESCE(n.module,'')) CONTAINS kw) THEN 0.005
                 WHEN any(kw IN ['test','spec','mock'] WHERE toLower(COALESCE(n.module,'')) CONTAINS kw) THEN 0.02
                 WHEN any(kw IN ['core','main','server','api'] WHERE toLower(COALESCE(n.module,'')) CONTAINS kw) THEN 0.01
                 ELSE 0.015
             END AS decay_rate
        WITH n, text_score + access * 0.3 + relevance * 2.0 * exp(-1.0 * decay_rate * days_since) AS score
        RETURN n.name AS name, labels(n)[0] AS type,
               LEFT(COALESCE(n.docstring,''), 120) AS doc,
               COALESCE(n.module,'') AS module
        ORDER BY score DESC
        LIMIT $limit
    """, keywords=keywords, limit=limit, ns=ns or "")
    return [dict(r) for r in result]


def _query_patterns(session, keywords: List[str], limit: int) -> List[dict]:
    """패턴/시드 데이터 폴백."""
    if limit <= 0:
        return []
    result = session.run("""
        UNWIND $keywords AS kw
        MATCH (n)
        WHERE any(lbl IN labels(n) WHERE lbl IN
            ['SecurityPattern','DesignPattern','BestPractice','CodeSmell','CodeConcept',
             'V3SecurityVulnerability','V3DesignPattern','V3BestPractice'])
          AND (toLower(n.name) CONTAINS toLower(kw)
            OR toLower(COALESCE(n.description,'')) CONTAINS toLower(kw)
            OR toLower(COALESCE(n.intent,'')) CONTAINS toLower(kw))
        RETURN DISTINCT n.name AS name, labels(n)[0] AS type,
               LEFT(COALESCE(n.description, n.intent, ''), 120) AS doc, '' AS module
        LIMIT $limit
    """, keywords=keywords, limit=limit)
    return [dict(r) for r in result]


def _save_cache(items: List[dict]):
    try:
        with open(CONTEXT_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"items": items, "timestamp": datetime.utcnow().isoformat()}, f, ensure_ascii=False)
    except Exception:
        pass


def _load_cache() -> List[dict]:
    try:
        if CONTEXT_CACHE_FILE.exists():
            return json.loads(CONTEXT_CACHE_FILE.read_text()).get("items", [])
    except Exception:
        pass
    return []

# ═══════════════════════════════════════════════════════════════════════════
# Detection + Output
# ═══════════════════════════════════════════════════════════════════════════

def get_user_prompt() -> str:
    prompt = os.environ.get("CLAUDE_USER_PROMPT", "")
    if not prompt:
        try:
            if not sys.stdin.isatty():
                prompt = sys.stdin.read()
        except Exception:
            pass  # stdin read best-effort
    return prompt.strip()


def detect_dev_context(prompt: str) -> Tuple[bool, List[str], int]:
    if not prompt:
        return False, [], 0
    prompt_lower = prompt.lower()
    detected, score = [], 0
    for kw, w in KEYWORD_WEIGHTS.items():
        if kw.lower() in prompt_lower:
            detected.append(kw)
            score += w
    for p in CODE_FILE_PATTERNS:
        if re.search(p, prompt, re.IGNORECASE):
            detected.append("code_file")
            score += 3
            break
    if "```" in prompt:
        detected.append("code_block")
        score += 3
    return score >= DEV_THRESHOLD, list(set(detected)), score


# Phase 1-3: Intent별 Token Budget
TOKEN_BUDGETS = {
    "REFACTOR":  {"max_items": 7, "max_doc": 200},
    "TEST":      {"max_items": 5, "max_doc": 300},
    "DEBUG":     {"max_items": 8, "max_doc": 150},
    "IMPLEMENT": {"max_items": 4, "max_doc": 100},
    "DESIGN":    {"max_items": 6, "max_doc": 250},
    "SECURITY":  {"max_items": 5, "max_doc": 200},
    "DOCUMENT":  {"max_items": 3, "max_doc": 500},
}


def _calc_relevance(item: dict, target: Optional[str], keywords: List[str]) -> float:
    """아이템별 관련성 점수 계산 (0.0~1.0)."""
    score = 0.0
    name = (item.get("name") or "").lower()
    doc = (item.get("doc") or "").lower()
    module = (item.get("module") or "").lower()

    # 타겟 매칭 (가장 높은 가중치)
    if target:
        t = target.lower()
        if name == t:
            score += 0.5
        elif t in name:
            score += 0.3
        elif t in doc or t in module:
            score += 0.15

    # 키워드 매칭
    kw_hits = 0
    for kw in keywords[:5]:
        kw_l = kw.lower()
        if kw_l in name:
            kw_hits += 2
        elif kw_l in doc:
            kw_hits += 1
    kw_max = max(len(keywords[:5]) * 2, 1)
    score += 0.3 * min(kw_hits / kw_max, 1.0)

    # 타입 보너스 (Function/Class > Module > Pattern)
    typ = item.get("type", "")
    if typ in ("Function", "Class"):
        score += 0.1
    elif typ == "Module":
        score += 0.05

    # docstring 존재 보너스
    if doc and len(doc) > 20:
        score += 0.1

    return min(score, 1.0)


def format_context(items: List[dict], intent: str, target: Optional[str],
                   keywords: List[str] = None) -> Tuple[str, dict]:
    """컨텍스트 포맷팅 + 관련성 메타데이터 반환."""
    if not items:
        return "", {"quality": "NONE", "relevance_pct": 0, "count": 0}

    keywords = keywords or []

    # Phase 1-3: Token Budget 적용
    budget = TOKEN_BUDGETS.get(intent, TOKEN_BUDGETS["IMPLEMENT"])
    items = items[:budget["max_items"]]
    max_doc = budget["max_doc"]

    # 관련성 점수 계산
    relevances = []
    for item in items:
        rel = _calc_relevance(item, target, keywords)
        item["_relevance"] = rel
        relevances.append(rel)

    avg_rel = sum(relevances) / max(len(relevances), 1)
    relevance_pct = int(avg_rel * 100)

    # 품질 등급
    if avg_rel >= 0.5:
        quality = "HIGH"
    elif avg_rel >= 0.25:
        quality = "MEDIUM"
    else:
        quality = "LOW"

    # 요약 키워드
    top_names = [it.get("name", "?") for it in sorted(items, key=lambda x: x.get("_relevance", 0), reverse=True)[:3]]
    summary = ", ".join(top_names)

    header = f'<knowledge-graph-context intent="{intent}"'
    if target:
        header += f' target="{target}"'
    header += f' items="{len(items)}" relevance="{relevance_pct}%" quality="{quality}" auto-injected="true">'
    lines = [header]
    for item in items:
        typ = item.get("type", "Unknown")
        name = item.get("name", "?")
        doc = item.get("doc", "").strip()[:max_doc]
        module = item.get("module", "")
        args = item.get("args", "")
        rel_pct = int(item.get("_relevance", 0) * 100)
        entry = f"  [{typ}] {name}"
        if module:
            entry += f" ({module})"
        if args and isinstance(args, str) and args != "":
            entry += f" args={args}"
        if doc:
            entry += f" - {doc}"
        lines.append(entry)
    lines.append("</knowledge-graph-context>")

    meta = {
        "quality": quality,
        "relevance_pct": relevance_pct,
        "count": len(items),
        "summary": summary,
        "per_item": [{"name": it.get("name", "?"), "rel": int(it.get("_relevance", 0)*100)} for it in items],
    }

    return "\n".join(lines), meta


def generate_output(session_id: str, intent: str, target: Optional[str],
                    search_kws: List[str], kg_context: str, score: int,
                    context_meta: dict = None) -> str:
    query_str = target if target else " ".join(search_kws[:3])
    parts = []
    if kg_context:
        parts.append(kg_context)

    intent_hint = {
        "REFACTOR": "Focus on call relationships and dependencies shown above.",
        "TEST": "Use the function signatures and module context above for test cases.",
        "DEBUG": "Trace the error through the call chain shown above.",
        "DESIGN": "Consider the architectural patterns and module structure above.",
        "SECURITY": "Check the security patterns and vulnerabilities shown above.",
        "DOCUMENT": "Use the function details and callers above to write documentation.",
        "IMPLEMENT": "Reference the existing code patterns above for consistency.",
    }

    # 관련성 메타 정보
    meta = context_meta or {}
    quality = meta.get("quality", "N/A")
    rel_pct = meta.get("relevance_pct", 0)
    count = meta.get("count", 0)
    summary = meta.get("summary", "")

    parts.append(f"""<system-reminder>
DEVELOPMENT CONTEXT DETECTED (session={session_id}, intent={intent}, score={score}{f', target={target}' if target else ''})
{f'KG context auto-injected ({count} items).' if kg_context else 'Neo4j unavailable - call MCP tools manually.'}
{intent_hint.get(intent, '')}

For deeper context, call:
1. mcp__neo4j-knowledge-graph__hybrid_search(query="{query_str}")
2. mcp__neo4j-knowledge-graph__smart_context(keywords={json.dumps(search_kws[:5])})
</system-reminder>""")

    return "\n".join(parts)

# ═══════════════════════════════════════════════════════════════════════════
# Session Tracking
# ═══════════════════════════════════════════════════════════════════════════

def log_and_track(is_dev: bool, keywords: List[str], session_id: str,
                  score: int, kg_injected: bool, intent: str, target: Optional[str]):
    log_file = Path.home() / ".claude" / "logs" / "mcp-kg-trigger.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "is_dev_context": is_dev, "score": score,
            "intent": intent, "target": target,
            "detected_keywords": keywords[:10],
            "session_id": session_id, "kg_injected": kg_injected,
            "project_dir": os.environ.get("CLAUDE_PROJECT_DIR", "unknown"),
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    if not (is_dev and session_id):
        return
    try:
        (ANALYTICS_DIR / "current_session.txt").write_text(session_id)
    except Exception:
        pass
    try:
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "session_start", "session_id": session_id,
            "keywords": keywords[:10], "score": score,
            "intent": intent, "target": target, "kg_injected": kg_injected,
        }
        with open(ANALYTICS_DIR / "sessions.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════


def get_modified_context() -> str:
    """Git status를 통해 최근 수정된 파일들의 컨텍스트(함수/클래스명 등)를 추출"""
    import subprocess
    import ast
    try:
        res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=1)
        if res.returncode != 0:
            return ""
        
        modified_files = []
        for line in res.stdout.splitlines():
            if line[:2] in (" M", "M ", "A ", "AM", "MM") and line.endswith(".py"):
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    modified_files.append(parts[1])
        
        context_parts = []
        for fpath in modified_files[:3]:
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        file_content = f.read()
                    tree = ast.parse(file_content)
                    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                    
                    info = f"File: {fpath}\n"
                    if classes: info += f"Classes: {', '.join(classes[:5])}\n"
                    if funcs: info += f"Functions: {', '.join(funcs[:10])}\n"
                    context_parts.append(info)
                except Exception:
                    pass
        return "\n".join(context_parts)
    except Exception:
        return ""

def main():
    try:
        prompt = get_user_prompt()
        if not prompt:
            sys.exit(0)

        is_dev, keywords, score = detect_dev_context(prompt)
        
        # 파일 변경 감지
        modified_ctx = get_modified_context()

        session_id = str(uuid.uuid4())[:12]

        intent = None
        target = None
        intent_source = "rule"
        
        # 완전 비개발 컨텍스트일지라도 LLM에게 최종 확인 (점수가 0이어도 변경된 파일이 있으면 개발 컨텍스트일 수 있음)
        if score > 0 or modified_ctx:
            try:
                from intent_classifier import classify_with_llm
                llm_result = classify_with_llm(prompt, context=modified_ctx)
                if llm_result:
                    is_dev = llm_result.get("is_dev_context", is_dev)
                    if llm_result.get("confidence", 0) >= 0.6:
                        intent = llm_result.get("intent")
                        target = llm_result.get("target")
                        intent_source = "llm"
            except Exception:
                pass

        if not is_dev:
            sys.exit(0)

        # 폴백: 규칙 기반 분류
        if not intent:
            intent = classify_intent(prompt)
        if not target:
            target = extract_target(prompt)

        # 검색 키워드 (타겟 우선)
        search_kws = []
        if target:
            search_kws.append(target)
        specific = [k for k in keywords if k not in ("code_file","code_block","코드","code","확인","check","추가","add")]
        search_kws.extend(specific[:3])
        search_kws = list(dict.fromkeys(search_kws))[:5] or ["code"]

        # Phase 3-2: Feedback-Driven Query Optimizer
        optimizer_hints = {"boost": [], "suppress": []}
        try:
            from query_optimizer import get_optimizer_hints
            optimizer_hints = get_optimizer_hints(intent)
            for node in optimizer_hints.get("boost", [])[:2]:
                if node not in search_kws:
                    search_kws.append(node)
            search_kws = search_kws[:7]
        except Exception:
            pass

        # ═══ Phase 5.2: Conversation-Aware Adaptive Context ═══
        conv_refinement = {}
        try:
            sys.path.insert(0, str(Path.home() / ".claude" / "kg-mcp-server"))
            from mcp_server.pipeline.adaptive_context import ConversationMemory
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
            conv_memory = ConversationMemory(project_dir)
            conv_refinement = conv_memory.get_search_refinement()

            # Boost: 반복 언급 엔티티 → 검색 키워드에 추가
            for entity in conv_refinement.get("boost_entities", [])[:2]:
                if entity not in search_kws:
                    search_kws.append(entity)

            # Suppress: 과다 노출 엔티티 → optimizer suppress에 추가
            for entity in conv_refinement.get("suppress_entities", []):
                if entity not in optimizer_hints.get("suppress", []):
                    optimizer_hints.setdefault("suppress", []).append(entity)

            search_kws = search_kws[:7]
        except Exception:
            pass

        # 새 프로젝트 자동 감지 + 벌크 인덱싱
        _auto_index_if_new_project()

        # Intent-Aware Neo4j 쿼리 (Phase 5.2: adaptive limit)
        adaptive_limit = conv_refinement.get("max_items", 5)
        kg_items = query_by_intent(intent, target, search_kws, limit=adaptive_limit)

        # suppress 노드 필터링 (Phase 3-2 + Phase 5.2 통합)
        suppress = set(optimizer_hints.get("suppress", []))
        already_injected = set(conv_refinement.get("already_injected", []))
        if suppress or already_injected:
            kg_items = [
                item for item in kg_items
                if item.get("name") not in suppress
                and item.get("name") not in already_injected
            ]

        kg_context, context_meta = format_context(kg_items, intent, target, keywords=search_kws)

        # Phase 10.5: Quality Gate — LOW 품질이면 주입 차단 (컨텍스트 오염 방지)
        quality = context_meta.get("quality", "NONE")
        rel_pct = context_meta.get("relevance_pct", 0)
        if quality == "LOW" or rel_pct < 20:
            print(f"⊘ [MCP-KG] Quality gate blocked: {quality} ({rel_pct}%) — skipping injection", file=sys.stderr)
            kg_context = ""  # 주입 차단
            kg_items = []

        log_and_track(is_dev, keywords, session_id, score, bool(kg_items), intent, target)

        # 피드백 루프용: 주입된 식별자 + 관련성 메타 저장
        injected_names = [item.get("name", "") for item in kg_items if item.get("name")]
        if injected_names:
            try:
                inj_file = ANALYTICS_DIR / "last_injected_identifiers.json"
                with open(inj_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "session_id": session_id,
                        "identifiers": injected_names,
                        "intent": intent,
                        "target": target,
                        "project_dir": os.environ.get("CLAUDE_PROJECT_DIR", ""),
                        "query": " ".join(search_kws[:3]),
                        "relevance": context_meta,
                    }, f, ensure_ascii=False)
            except Exception:
                pass

        # Phase 5.2: 대화 메모리 업데이트 (턴 기록)
        try:
            if conv_memory:
                conv_memory.update_turn(intent, target, keywords, injected_names)
                transition = conv_memory.detect_intent_transition()
                if transition:
                    print(f"⚡ [MCP-KG] Intent transition: {transition['from']} → {transition['to']}", file=sys.stderr)
        except Exception:
            pass

        output = generate_output(session_id, intent, target, search_kws, kg_context, score, context_meta)
        print(output)

        q = context_meta.get("quality", "?")
        r = context_meta.get("relevance_pct", 0)
        print(f"✓ [MCP-KG] session={session_id} intent={intent}({intent_source}) target={target} neo4j={len(kg_items)}items relevance={r}%({q})", file=sys.stderr)

    except Exception as e:
        print(f"[MCP-KG] Error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
