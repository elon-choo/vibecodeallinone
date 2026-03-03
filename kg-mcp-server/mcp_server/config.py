"""MCP 서버 설정"""
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    """서버 설정"""
    # Neo4j
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")

    # 컨텍스트 설정
    max_tokens: int = 4000
    search_limit: int = 20
    rerank_limit: int = 10

    # 리랭킹 가중치
    bm25_weight: float = 0.3
    semantic_weight: float = 0.7
    vector_weight: float = 0.5  # Phase 7.6: 벤치마크 기반 최적화 (0.4 → 0.5, vector P@1=0.48 > keyword P@1=0.38)

    # Phase 10: Embedding 설정 (voyage-code-3 — 코드 전용 SOTA, 13-17% 향상)
    embedding_model: str = "voyage-code-3"
    embedding_dimensions: int = 1024
    embedding_provider: str = "voyage"  # "openai" or "voyage"
    voyage_api_key: str = os.getenv("VOYAGE_API_KEY", "")

    # 프로젝트 루트
    project_root: Path = Path(__file__).parent.parent

config = Config()
