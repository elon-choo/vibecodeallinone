"""MCP 서버 설정"""
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# power-pack.env에서 환경변수 로드 (fallback: ~/.env)
_env_file = os.path.expanduser("~/.claude/power-pack.env")
if not os.path.exists(_env_file):
    _env_file = os.path.expanduser("~/.env")
if os.path.exists(_env_file):
    load_dotenv(_env_file)


def _get_env(key: str, default: str = "") -> str:
    """Read env var at access time, not import time."""
    return os.getenv(key, default)


@dataclass
class Config:
    """서버 설정 — env vars are read lazily via properties."""
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

    # 프로젝트 루트
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)

    @property
    def neo4j_uri(self) -> str:
        return _get_env("NEO4J_URI", "bolt://localhost:7687")

    @property
    def neo4j_user(self) -> str:
        return _get_env("NEO4J_USERNAME", "neo4j")

    @property
    def neo4j_password(self) -> str:
        pw = _get_env("NEO4J_PASSWORD", "")
        if not pw:
            logger.warning("NEO4J_PASSWORD is empty — authentication will likely fail. Set NEO4J_PASSWORD env var.")
        return pw

    @property
    def voyage_api_key(self) -> str:
        return _get_env("VOYAGE_API_KEY", "")


config = Config()
