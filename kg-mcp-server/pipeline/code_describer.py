"""
LLM Code Describer (Phase 10.4)
================================
docstring이 없는 함수/클래스에 대해 Gemini Flash로 1-2문장 자연어 설명을 자동 생성합니다.

Qodo 추천 "dual storage" 전략:
- 코드 본문과 함께 자연어 설명을 저장
- 벡터 검색 시 코드+설명 모두 임베딩에 포함
- 자연어 쿼리와 코드 간 의미적 갭(semantic gap) 해소
"""

import json
import logging
import os
import time
from typing import Dict, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(os.path.expanduser("~/.env"))
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

DESCRIBE_PROMPT = """You are a senior developer writing concise function/class descriptions for a code search index.

Given the code below, write a 1-2 sentence description in English that explains:
- What this function/class DOES (its purpose)
- Key behaviors (API calls, data transformations, side effects)

Rules:
- Be specific, not generic (bad: "handles data", good: "fetches pending members from Supabase and returns filtered list")
- Include domain terms that a developer would search for
- Maximum 150 characters
- Do NOT include the function name in the description
- Respond with ONLY the description text, nothing else

Code:
```
{code}
```"""

BATCH_DESCRIBE_PROMPT = """You are a senior developer writing concise code descriptions for a search index.

For each function below, write a 1-2 sentence description (max 150 chars) explaining what it does.
Be specific about behaviors (API calls, data transforms, side effects).

Respond in JSON array format ONLY: ["description1", "description2", ...]

Functions:
{functions}"""


class CodeDescriber:
    """Gemini Flash 기반 코드 설명 자동 생성기."""

    def __init__(self, driver, model_name: str = "gemini-3-flash-preview"):
        self.driver = driver
        self.model = genai.GenerativeModel(model_name)
        self._request_count = 0
        self._minute_start = time.time()

    def _rate_limit(self):
        """분당 15 요청 제한 (Gemini free tier)."""
        now = time.time()
        if now - self._minute_start >= 60:
            self._request_count = 0
            self._minute_start = now
        if self._request_count >= 14:
            sleep_time = 60 - (now - self._minute_start) + 1
            logger.info(f"Rate limit: sleeping {sleep_time:.0f}s")
            time.sleep(sleep_time)
            self._request_count = 0
            self._minute_start = time.time()

    def describe_single(self, code: str) -> Optional[str]:
        """단일 코드에 대한 설명 생성."""
        if not code or not code.strip():
            return None

        # 코드를 1500자로 제한 (토큰 절약)
        truncated = code[:1500]
        prompt = DESCRIBE_PROMPT.format(code=truncated)

        self._rate_limit()
        try:
            response = self.model.generate_content(prompt)
            self._request_count += 1
            text = response.text.strip()
            # 150자 제한
            if len(text) > 200:
                text = text[:197] + "..."
            return text
        except Exception as e:
            logger.warning(f"Gemini describe failed: {e}")
            return None

    def describe_batch(self, codes: List[Dict[str, str]]) -> List[Optional[str]]:
        """배치 코드 설명 생성 (최대 10개씩).

        Args:
            codes: [{"name": "fetchMembers", "code": "..."}, ...]
        Returns:
            설명 리스트 (실패 시 None)
        """
        if not codes:
            return []

        # 배치 프롬프트 구성
        func_texts = []
        for i, c in enumerate(codes):
            snippet = (c.get("code") or "")[:800]
            name = c.get("name", f"func_{i}")
            func_texts.append(f"[{i}] {name}:\n```\n{snippet}\n```")

        prompt = BATCH_DESCRIBE_PROMPT.format(functions="\n\n".join(func_texts))

        self._rate_limit()
        try:
            response = self.model.generate_content(prompt)
            self._request_count += 1
            text = response.text.strip()

            # JSON 파싱
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            descriptions = json.loads(text)
            if isinstance(descriptions, list) and len(descriptions) == len(codes):
                return [d[:200] if d else None for d in descriptions]
            else:
                logger.warning(f"Batch response mismatch: expected {len(codes)}, got {len(descriptions) if isinstance(descriptions, list) else 'not a list'}")
                return [None] * len(codes)

        except Exception as e:
            logger.warning(f"Batch describe failed: {e}")
            return [None] * len(codes)

    def enrich_nodes_without_docs(self, namespace: Optional[str] = None,
                                   limit: int = 500, dry_run: bool = False) -> Dict:
        """docstring이 없고 code가 있는 노드에 AI 설명 추가.

        Args:
            namespace: 특정 네임스페이스만 처리 (None이면 전체)
            limit: 최대 처리 수
            dry_run: True면 저장 안함

        Returns:
            통계 딕셔너리
        """
        stats = {"total": 0, "described": 0, "failed": 0, "skipped": 0}

        # docstring 없고, code 있고, ai_description 없는 노드
        ns_filter = "AND n.namespace = $ns" if namespace else ""
        with self.driver.session() as s:
            nodes = s.run(f"""
                MATCH (n) WHERE (n:Function OR n:Class)
                AND (n.docstring IS NULL OR n.docstring = '')
                AND n.code IS NOT NULL AND n.code <> ''
                AND n.ai_description IS NULL
                {ns_filter}
                RETURN elementId(n) as eid, n.name as name, n.code as code,
                       n.module as module, n.namespace as ns
                LIMIT $limit
            """, ns=namespace, limit=limit).data()

        stats["total"] = len(nodes)
        if not nodes:
            logger.info("No nodes to describe")
            return stats

        logger.info(f"Found {len(nodes)} nodes without descriptions")

        # 10개씩 배치 처리
        batch_size = 10
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            codes = [{"name": n["name"], "code": n["code"]} for n in batch]

            descriptions = self.describe_batch(codes)

            for node, desc in zip(batch, descriptions):
                if desc:
                    if dry_run:
                        logger.info(f"  [DRY-RUN] {node['name']}: {desc}")
                        stats["described"] += 1
                    else:
                        try:
                            with self.driver.session() as s:
                                s.run("""
                                    MATCH (n) WHERE elementId(n) = $eid
                                    SET n.ai_description = $desc,
                                        n.ai_described_at = datetime()
                                """, eid=node["eid"], desc=desc)
                            stats["described"] += 1
                        except Exception as e:
                            logger.warning(f"Failed to save description for {node['name']}: {e}")
                            stats["failed"] += 1
                else:
                    stats["skipped"] += 1

            logger.info(f"  Batch {i // batch_size + 1}: {len(batch)} processed")

        return stats

    def describe_on_sync(self, node_name: str, code: str) -> Optional[str]:
        """write_back sync 시 호출: 단일 노드에 대한 설명 생성.

        코드가 짧으면 (< 50자) 설명 불필요로 판단.
        """
        if not code or len(code.strip()) < 50:
            return None
        return self.describe_single(code)
