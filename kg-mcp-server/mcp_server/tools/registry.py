"""Component Registry — lightweight dependency injection container.

Holds all pipeline component instances so that server.py doesn't directly
instantiate them and handlers can be unit-tested with substituted components.
"""

import logging
from typing import Optional

from mcp_server.config import config

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """Holds all pipeline component instances, created lazily on connect()."""

    def __init__(self):
        self.neo4j_driver = None
        self.searcher = None
        self.builder = None
        self.reranker = None
        self.query_router = None
        self.hybrid_search = None
        self.write_back = None
        self.impact_simulator = None
        self.weight_learner = None
        self.bug_radar = None
        self.auto_test_gen = None
        self.ontology_evolver = None
        self.knowledge_transfer = None
        self.llm_judge = None
        self.vector_search_engine = None
        self.rag_engine = None
        self.doc_generator = None
        self.shared_memory = None
        self.code_assist = None

    @property
    def connected(self) -> bool:
        return self.searcher is not None

    def connect(self):
        """Lazily create a Neo4j driver and all pipeline components.

        Core components (searcher, builder, reranker, query_router,
        hybrid_search, write_back) are required — a failure raises
        ``ConnectionError``.  All other components are optional: a
        failure is logged but the server continues with that component
        set to ``None`` (handlers already guard against ``None``).
        """
        if self.connected:
            return

        from mcp_server.pipeline.graph_search import GraphSearcher
        from mcp_server.pipeline.context_builder import ContextBuilder, SimpleReranker
        from mcp_server.pipeline.query_router import QueryRouter
        from mcp_server.pipeline.hybrid_search import HybridSearchEngine
        from mcp_server.pipeline.write_back import GraphWriteBack

        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                config.neo4j_uri,
                auth=(config.neo4j_user, config.neo4j_password)
            )
            self.neo4j_driver = driver

            # --- Core components (required) ---
            self.builder = ContextBuilder(max_tokens=config.max_tokens)
            self.reranker = SimpleReranker()
            self.query_router = QueryRouter()
            self.searcher = GraphSearcher.from_driver(driver)
            self.hybrid_search = HybridSearchEngine(driver)
            self.write_back = GraphWriteBack(driver)

            self._ensure_neo4j_indexes(driver)
            logger.info("Neo4j core components connected successfully")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            raise ConnectionError(f"Neo4j connection failed: {e}") from e

        # --- Optional components (failure is non-fatal) ---
        self._init_optional(driver)

    def _init_optional(self, driver):
        """Instantiate optional pipeline components with per-component error isolation."""
        optional_components = [
            ("impact_simulator", "mcp_server.pipeline.impact_simulator", "ImpactSimulator"),
            ("weight_learner", "mcp_server.pipeline.weight_learner", "NodeWeightLearner"),
            ("bug_radar", "mcp_server.pipeline.bug_radar", "BugRadar"),
            ("auto_test_gen", "mcp_server.pipeline.auto_test_gen", "AutoTestGenerator"),
            ("ontology_evolver", "mcp_server.pipeline.ontology_evolver", "OntologyEvolver"),
            ("knowledge_transfer", "mcp_server.pipeline.knowledge_transfer", "KnowledgeTransfer"),
            ("llm_judge", "mcp_server.pipeline.llm_judge", "LLMJudge"),
            ("vector_search_engine", "mcp_server.pipeline.vector_search", "VectorSearchEngine"),
            ("rag_engine", "mcp_server.pipeline.rag_engine", "RAGEngine"),
            ("doc_generator", "mcp_server.pipeline.doc_generator", "DocGenerator"),
            ("shared_memory", "mcp_server.pipeline.shared_memory", "SharedMemoryPool"),
            ("code_assist", "mcp_server.pipeline.code_assist", "CodeAssist"),
        ]

        import importlib

        for attr, module_path, class_name in optional_components:
            try:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                setattr(self, attr, cls(driver))
            except Exception as e:
                logger.warning(f"Optional component {class_name} failed to init (non-fatal): {e}")
                # attribute stays None — handlers already check for None

    @staticmethod
    def _ensure_neo4j_indexes(driver):
        """Neo4j B-Tree 인덱스 자동 생성."""
        index_queries = [
            "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.name, f.file_path)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.name, c.file_path)",
            "CREATE INDEX IF NOT EXISTS FOR (fi:File) ON (fi.path)",
        ]
        try:
            with driver.session() as session:
                for query in index_queries:
                    session.run(query)
            logger.info("Neo4j indexes verified/created (Function, Class, File)")
        except Exception as e:
            logger.warning(f"Neo4j index creation failed (non-fatal): {e}")

    def close(self):
        """Close Neo4j driver and clean up."""
        if self.neo4j_driver is not None:
            try:
                self.neo4j_driver.close()
                logger.info("Neo4j driver closed")
            except Exception as e:
                logger.warning(f"Error closing Neo4j driver: {e}")
            self.neo4j_driver = None
        if self.searcher is not None:
            try:
                self.searcher.close()
            except Exception:
                pass
            self.searcher = None
