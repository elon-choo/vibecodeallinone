"""Tool handler package — split by domain concern.

Re-exports ``build_dispatch_table`` so existing imports like
``from mcp_server.tools.handlers import build_dispatch_table``
continue to work unchanged.
"""

from .search import (
    search_knowledge, get_function_context, get_module_structure,
    get_security_patterns, get_graph_stats, smart_context,
    hybrid_search, get_call_graph, get_similar_code,
)
from .analytics import (
    get_cache_stats_v2, get_analytics_summary_handler,
    get_top_referenced, get_recent_activity, get_quality_report,
)
from .writeback import (
    provide_feedback, simulate_impact, sync_incremental,
    evolve_ontology, promote_pattern, get_global_insights,
    suggest_tests, get_bug_hotspots,
)
from .session import get_session_context
from .ai import semantic_search, ask_codebase, evaluate_code, assist_code, generate_docs
from .shared_memory import get_shared_context, publish_context
from .indexing import index_project


def build_dispatch_table(registry):
    """Build the tool name -> handler function dispatch table."""
    return {
        "search_knowledge": lambda args: search_knowledge(registry, args),
        "get_function_context": lambda args: get_function_context(registry, args),
        "get_module_structure": lambda args: get_module_structure(registry, args),
        "get_security_patterns": lambda args: get_security_patterns(registry, args),
        "get_graph_stats": lambda args: get_graph_stats(registry, args),
        "smart_context": lambda args: smart_context(registry, args),
        "hybrid_search": lambda args: hybrid_search(registry, args),
        "get_call_graph": lambda args: get_call_graph(registry, args),
        "get_similar_code": lambda args: get_similar_code(registry, args),
        "get_cache_stats": lambda args: get_cache_stats_v2(registry, args),
        "get_analytics_summary": lambda args: get_analytics_summary_handler(registry, args),
        "get_top_referenced": lambda args: get_top_referenced(registry, args),
        "get_recent_activity": lambda args: get_recent_activity(registry, args),
        "get_session_context": lambda args: get_session_context(registry, args),
        "evolve_ontology": lambda args: evolve_ontology(registry, args),
        "promote_pattern": lambda args: promote_pattern(registry, args),
        "get_global_insights": lambda args: get_global_insights(registry, args),
        "suggest_tests": lambda args: suggest_tests(registry, args),
        "get_bug_hotspots": lambda args: get_bug_hotspots(registry, args),
        "provide_feedback": lambda args: provide_feedback(registry, args),
        "simulate_impact": lambda args: simulate_impact(registry, args),
        "sync_incremental": lambda args: sync_incremental(registry, args),
        "evaluate_code": lambda args: evaluate_code(registry, args),
        "semantic_search": lambda args: semantic_search(registry, args),
        "ask_codebase": lambda args: ask_codebase(registry, args),
        "generate_docs": lambda args: generate_docs(registry, args),
        "assist_code": lambda args: assist_code(registry, args),
        "get_shared_context": lambda args: get_shared_context(registry, args),
        "publish_context": lambda args: publish_context(registry, args),
        "get_quality_report": lambda args: get_quality_report(registry, args),
        "index_project": lambda args: index_project(registry, args),
    }
