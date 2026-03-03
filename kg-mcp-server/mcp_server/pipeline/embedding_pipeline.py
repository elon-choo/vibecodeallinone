"""
Embedding Pipeline (Phase 10)
==============================
voyage-code-3 (코드 전용 SOTA, 79.23% CoIR) + OpenAI fallback.
코드 검색 정확도 13-17% 향상.

Features:
- voyage-code-3 기본 (1024 차원, 코드 전용 최적화)
- OpenAI fallback (text-embedding-3-small, 1536 차원)
- Neo4j Vector Index 생성 (cosine similarity)
- 전체 노드 벌크 임베딩 + 증분 임베딩
- Exponential backoff on rate limit errors
"""

import os
import time
import logging
from typing import List, Dict, Optional, Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ~/.claude/power-pack.env에서 API 키 로드 (fallback: ~/.env)
_env_file = os.path.expanduser("~/.claude/power-pack.env")
if not os.path.exists(_env_file):
    _env_file = os.path.expanduser("~/.env")
load_dotenv(_env_file)

# 프로바이더 감지
_VOYAGE_KEY = os.getenv("VOYAGE_API_KEY", "")
_PROVIDER = "voyage" if _VOYAGE_KEY else "openai"

if _PROVIDER == "voyage":
    import voyageai
    EMBEDDING_MODEL = "voyage-code-3"
    EMBEDDING_DIMENSIONS = 1024
    MAX_BATCH_SIZE = 128  # Voyage 배치 제한
    logger.info("Embedding provider: Voyage (voyage-code-3, 1024d)")
else:
    from openai import OpenAI, RateLimitError, APIError
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    MAX_BATCH_SIZE = 2048
    logger.info("Embedding provider: OpenAI (text-embedding-3-small, 1536d)")

DEFAULT_PROCESS_BATCH = 100
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
RPM_LIMIT = 3000 if _PROVIDER == "openai" else 300  # Voyage RPM 제한
RPM_SAFETY_MARGIN = 0.8


class EmbeddingPipeline:
    """
    Neo4j Function/Class 노드에 임베딩 벡터를 생성하고 저장하는 파이프라인.
    voyage-code-3 (코드 전용 SOTA) 기본, OpenAI fallback.
    """

    def __init__(self, driver):
        self.driver = driver
        self.provider = _PROVIDER
        if self.provider == "voyage":
            self.voyage_client = voyageai.Client(api_key=_VOYAGE_KEY)
        else:
            self.client = OpenAI()
        self._request_count = 0
        self._minute_start = time.time()

    # ──────────────────────────────────────────────
    # 1. 텍스트 임베딩
    # ──────────────────────────────────────────────

    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트를 임베딩 벡터로 변환."""
        if not text or not text.strip():
            raise ValueError("Empty text cannot be embedded")
        result = self._call_embed_with_retry([text])
        return result[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """배치 텍스트를 임베딩 벡터로 변환."""
        if not texts:
            return []
        all_embeddings = []
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            chunk = texts[i:i + MAX_BATCH_SIZE]
            safe_chunk = [t if t and t.strip() else "empty" for t in chunk]
            embeddings = self._call_embed_with_retry(safe_chunk)
            all_embeddings.extend(embeddings)
        return all_embeddings

    def _call_embed_with_retry(self, texts: List[str]) -> List[List[float]]:
        """임베딩 API 호출 + exponential backoff (Voyage/OpenAI 자동 분기)."""
        self._check_rate_limit()
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                if self.provider == "voyage":
                    result = self.voyage_client.embed(
                        texts,
                        model=EMBEDDING_MODEL,
                        input_type="document",
                    )
                    self._request_count += 1
                    return result.embeddings
                else:
                    response = self.client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=texts,
                        dimensions=EMBEDDING_DIMENSIONS,
                    )
                    self._request_count += 1
                    return [item.embedding for item in response.data]

            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "rate" in err_str or "429" in err_str or "limit" in err_str
                if attempt < MAX_RETRIES - 1:
                    wait_time = backoff * (2 ** attempt)
                    logger.warning(f"{'Rate limit' if is_rate_limit else 'API error'} "
                                   f"(attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                                   f"Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {MAX_RETRIES} retries: {e}")
                    raise

        raise RuntimeError("Unexpected state in retry loop")

    def _check_rate_limit(self):
        """
        분당 요청 수 제한 관리.
        RPM_LIMIT * RPM_SAFETY_MARGIN에 도달하면 남은 시간만큼 대기.
        """
        now = time.time()
        elapsed = now - self._minute_start

        if elapsed >= 60:
            # 새 분 시작
            self._request_count = 0
            self._minute_start = now
            return

        effective_limit = int(RPM_LIMIT * RPM_SAFETY_MARGIN)
        if self._request_count >= effective_limit:
            sleep_time = 60 - elapsed + 0.5
            logger.info(
                f"Rate limit approaching ({self._request_count}/{RPM_LIMIT} RPM). "
                f"Sleeping {sleep_time:.1f}s..."
            )
            time.sleep(sleep_time)
            self._request_count = 0
            self._minute_start = time.time()

    # ──────────────────────────────────────────────
    # 2. 노드 텍스트 조합
    # ──────────────────────────────────────────────

    def build_embed_text(self, node: dict) -> str:
        """
        노드 속성에서 임베딩할 텍스트를 조합.

        Phase 10.4 업데이트: code body + ai_description 추가
        조합 규칙 (우선순위):
        1. qualified_name 또는 name (항상)
        2. docstring 또는 ai_description (자연어 설명)
        3. code body (첫 500자, 코드 의미 파악용)
        4. args (시그니처)
        5. module (모듈 경로)

        Args:
            node: Neo4j 노드 속성 딕셔너리

        Returns:
            임베딩에 사용할 텍스트 문자열
        """
        parts = []

        # 1. qualified_name 또는 name
        qname = node.get("qualified_name") or node.get("qname")
        name = node.get("name", "")

        if qname:
            parts.append(qname)
        elif name:
            parts.append(name)

        # 2. 자연어 설명 (docstring > ai_description)
        docstring = node.get("docstring") or node.get("doc") or ""
        ai_desc = node.get("ai_description") or ""
        if isinstance(docstring, list):
            docstring = " ".join(str(d) for d in docstring)
        if isinstance(ai_desc, list):
            ai_desc = " ".join(str(d) for d in ai_desc)

        if docstring and isinstance(docstring, str) and docstring.strip():
            parts.append(docstring.strip()[:500])
        elif ai_desc and isinstance(ai_desc, str) and ai_desc.strip():
            parts.append(ai_desc.strip())

        # 3. args (함수 시그니처)
        args = node.get("args") or ""
        if isinstance(args, list):
            args = ", ".join(str(a) for a in args)
        if args and isinstance(args, str) and args.strip():
            parts.append(f"args: {args.strip()}")

        # 4. 모듈 정보
        module = node.get("module") or ""
        if isinstance(module, list):
            module = ".".join(str(m) for m in module)
        if module and isinstance(module, str) and module.strip():
            parts.append(f"module: {module.strip()}")

        text = "\n".join(parts)

        # 빈 텍스트 방지
        if not text.strip():
            text = name or "unknown"

        return text

    # ──────────────────────────────────────────────
    # 3. 벌크 임베딩
    # ──────────────────────────────────────────────

    def embed_all_nodes(self, batch_size: int = DEFAULT_PROCESS_BATCH) -> dict:
        """
        embedding이 없는 모든 Function/Class 노드에 대해 벌크 임베딩 수행.

        Args:
            batch_size: 한 번에 처리할 노드 수 (기본 100)

        Returns:
            통계 딕셔너리:
            {
                "total_processed": int,
                "total_embedded": int,
                "total_skipped": int,
                "total_errors": int,
                "elapsed_seconds": float,
            }
        """
        start_time = time.time()
        total_processed = 0
        total_embedded = 0
        total_skipped = 0
        total_errors = 0

        logger.info("Starting bulk embedding pipeline...")

        # 임베딩이 없는 노드 총 개수 파악
        with self.driver.session() as session:
            count_result = session.run("""
                MATCH (n)
                WHERE (n:Function OR n:Class OR n:DesignPattern OR n:Strategy)
                AND n.embedding IS NULL
                RETURN count(n) as cnt
            """)
            total_remaining = count_result.single()["cnt"]

        logger.info(f"Found {total_remaining} nodes without embeddings")

        if total_remaining == 0:
            logger.info("All nodes already have embeddings. Nothing to do.")
            return {
                "total_processed": 0,
                "total_embedded": 0,
                "total_skipped": 0,
                "total_errors": 0,
                "elapsed_seconds": 0.0,
            }

        # 배치 처리 루프
        while True:
            # 임베딩 없는 노드 배치 가져오기
            with self.driver.session() as session:
                batch_result = session.run("""
                    MATCH (n)
                    WHERE (n:Function OR n:Class OR n:DesignPattern OR n:Strategy)
                    AND n.embedding IS NULL
                    RETURN
                        elementId(n) as element_id,
                        labels(n) as labels,
                        n.name as name,
                        n.qualified_name as qualified_name,
                        n.docstring as docstring,
                        n.args as args,
                        n.module as module,
                        n.code as code,
                        n.ai_description as ai_description
                    LIMIT $batch_size
                """, batch_size=batch_size)

                nodes = [dict(record) for record in batch_result]

            if not nodes:
                break

            # 텍스트 조합
            texts = []
            valid_nodes = []
            for node in nodes:
                try:
                    text = self.build_embed_text(node)
                    texts.append(text)
                    valid_nodes.append(node)
                except Exception as e:
                    logger.warning(f"Failed to build text for {node.get('name')}: {e}")
                    total_skipped += 1

            if not texts:
                total_processed += len(nodes)
                continue

            # 배치 임베딩
            try:
                embeddings = self.embed_batch(texts)
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                total_errors += len(texts)
                total_processed += len(nodes)
                continue

            # Neo4j에 저장
            for node, embedding in zip(valid_nodes, embeddings):
                try:
                    self._save_embedding(node["element_id"], embedding)
                    total_embedded += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to save embedding for {node.get('name')}: {e}"
                    )
                    total_errors += 1

            total_processed += len(nodes)

            # 진행률 로깅 (100개마다)
            if total_processed % 100 == 0 or total_processed >= total_remaining:
                elapsed = time.time() - start_time
                rate = total_embedded / elapsed if elapsed > 0 else 0
                logger.info(
                    f"Progress: {total_processed}/{total_remaining} processed, "
                    f"{total_embedded} embedded, {total_errors} errors, "
                    f"{rate:.1f} nodes/sec"
                )

        elapsed = time.time() - start_time
        stats = {
            "total_processed": total_processed,
            "total_embedded": total_embedded,
            "total_skipped": total_skipped,
            "total_errors": total_errors,
            "elapsed_seconds": round(elapsed, 2),
        }

        logger.info(
            f"Bulk embedding complete: {total_embedded}/{total_processed} nodes "
            f"in {elapsed:.1f}s ({total_errors} errors)"
        )

        return stats

    def _save_embedding(self, element_id: str, embedding: List[float]):
        """
        단일 노드에 임베딩 벡터를 저장.

        Args:
            element_id: Neo4j elementId
            embedding: 1536차원 벡터
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (n)
                WHERE elementId(n) = $element_id
                SET n.embedding = $embedding
                SET n.embedding_model = $model
                SET n.embedded_at = datetime()
            """, element_id=element_id, embedding=embedding, model=EMBEDDING_MODEL)

    # ──────────────────────────────────────────────
    # 4. 단일 노드 증분 임베딩
    # ──────────────────────────────────────────────

    def embed_single_node(self, node_name: str) -> bool:
        """
        단일 노드에 대해 임베딩 생성/업데이트.
        write_back.sync_file() 후 자동 호출용.

        Args:
            node_name: 노드 이름 (Function 또는 Class)

        Returns:
            성공 여부
        """
        try:
            # 노드 조회
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    WHERE (n:Function OR n:Class)
                    AND n.name = $name
                    RETURN
                        elementId(n) as element_id,
                        labels(n) as labels,
                        n.name as name,
                        n.qualified_name as qualified_name,
                        n.docstring as docstring,
                        n.args as args,
                        n.module as module
                    LIMIT 1
                """, name=node_name)

                record = result.single()

            if not record:
                logger.debug(f"Node not found for embedding: {node_name}")
                return False

            node = dict(record)

            # 텍스트 조합 및 임베딩
            text = self.build_embed_text(node)
            embedding = self.embed_text(text)

            # 저장
            self._save_embedding(node["element_id"], embedding)

            logger.debug(f"Embedded node: {node_name}")
            return True

        except Exception as e:
            logger.warning(f"Failed to embed node {node_name}: {e}")
            return False

    # ──────────────────────────────────────────────
    # 5. Vector Index 생성
    # ──────────────────────────────────────────────

    def create_vector_index(self):
        """
        Neo4j Vector Index 생성 (Function, Class 각각).
        이미 존재하면 무시 (IF NOT EXISTS).
        """
        indexes = [
            {
                "name": "code_embeddings",
                "label": "Function",
            },
            {
                "name": "class_embeddings",
                "label": "Class",
            },
        ]

        with self.driver.session() as session:
            for idx in indexes:
                try:
                    query = f"""
                        CREATE VECTOR INDEX {idx['name']} IF NOT EXISTS
                        FOR (n:{idx['label']})
                        ON (n.embedding)
                        OPTIONS {{indexConfig: {{
                            `vector.dimensions`: {EMBEDDING_DIMENSIONS},
                            `vector.similarity_function`: 'cosine'
                        }}}}
                    """
                    session.run(query)
                    logger.info(
                        f"Vector index '{idx['name']}' created/verified "
                        f"for :{idx['label']} (dim={EMBEDDING_DIMENSIONS}, cosine)"
                    )
                except Exception as e:
                    # Neo4j Community Edition은 vector index를 지원하지 않을 수 있음
                    logger.warning(
                        f"Failed to create vector index '{idx['name']}': {e}"
                    )

    # ──────────────────────────────────────────────
    # 6. 통계
    # ──────────────────────────────────────────────

    def get_embedding_stats(self) -> dict:
        """
        임베딩 통계 조회.

        Returns:
            {
                "total_nodes": int,          # Function+Class 전체 노드 수
                "embedded_nodes": int,       # 임베딩 완료 노드 수
                "pending_nodes": int,        # 미완료 노드 수
                "coverage_percent": float,   # 커버리지 비율
                "model": str,                # 사용 모델명
                "dimensions": int,           # 임베딩 차원
            }
        """
        with self.driver.session() as session:
            # 전체 노드 수
            total_result = session.run("""
                MATCH (n)
                WHERE n:Function OR n:Class OR n:DesignPattern OR n:Strategy
                RETURN count(n) as total
            """)
            total = total_result.single()["total"]

            # 임베딩 완료 노드 수
            embedded_result = session.run("""
                MATCH (n)
                WHERE (n:Function OR n:Class OR n:DesignPattern OR n:Strategy)
                AND n.embedding IS NOT NULL
                RETURN count(n) as embedded
            """)
            embedded = embedded_result.single()["embedded"]

        pending = total - embedded
        coverage = (embedded / total * 100) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "embedded_nodes": embedded,
            "pending_nodes": pending,
            "coverage_percent": round(coverage, 2),
            "model": EMBEDDING_MODEL,
            "dimensions": EMBEDDING_DIMENSIONS,
        }

    # ──────────────────────────────────────────────
    # 7. 벡터 유사도 검색 (보너스)
    # ──────────────────────────────────────────────

    def vector_search(
        self,
        query_text: str,
        label: str = "Function",
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        벡터 유사도 기반 검색 (Vector Index 사용).

        Args:
            query_text: 검색할 텍스트
            label: 검색 대상 레이블 ("Function" 또는 "Class")
            top_k: 반환할 최대 결과 수

        Returns:
            유사한 노드 리스트 (score 포함)
        """
        index_name = "code_embeddings" if label == "Function" else "class_embeddings"

        # 쿼리 텍스트 임베딩
        query_embedding = self.embed_text(query_text)

        with self.driver.session() as session:
            result = session.run(f"""
                CALL db.index.vector.queryNodes('{index_name}', $top_k, $embedding)
                YIELD node, score
                RETURN
                    node.name as name,
                    node.qualified_name as qualified_name,
                    node.docstring as docstring,
                    node.module as module,
                    labels(node) as labels,
                    score
                ORDER BY score DESC
            """, top_k=top_k, embedding=query_embedding)

            return [dict(record) for record in result]
