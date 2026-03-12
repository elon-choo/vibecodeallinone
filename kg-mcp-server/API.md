# KG MCP Server — API Reference

Complete reference for all 27 MCP tools exposed by the Knowledge Graph server.

## Connection

The server communicates over **stdio** using the MCP JSON-RPC protocol.
Configure it in your MCP client (Claude Code, Cursor, etc.) as described in the project README.

---

## Tools

### Search & Discovery

#### `search_knowledge`
Search the knowledge graph for code, patterns, and security information.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | **yes** | — | Search query (function name, class name, pattern, keyword) |
| `type` | string | no | `"all"` | `"code"`, `"pattern"`, or `"all"` |
| `limit` | integer | no | `10` | Maximum number of results |

**Returns:** JSON array of matching knowledge nodes with name, type, description, and relevance score.

---

#### `hybrid_search`
Hybrid search combining keyword + graph traversal. Auto-routes between Local and Global search strategies.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | **yes** | — | Search query |
| `limit` | integer | no | `10` | Maximum number of results |

**Returns:** Fused results from BM25 keyword search and graph-based search, ranked by combined relevance.

---

#### `semantic_search`
Vector-based semantic search using natural language queries.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | **yes** | — | Natural language query (e.g. `"async file reading"`, `"error handling pattern"`) |
| `limit` | integer | no | `10` | Maximum number of results |
| `threshold` | number | no | `0.7` | Cosine similarity threshold (0.0–1.0) |

**Returns:** Matching code nodes sorted by cosine similarity, filtered by threshold.

---

#### `get_similar_code`
Find functions with similar functionality based on docstring embeddings.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | **yes** | — | Description of desired functionality |
| `limit` | integer | no | `5` | Maximum number of results |

**Returns:** Similar functions with similarity scores.

---

#### `ask_codebase`
Answer natural language questions about the codebase by searching and synthesizing relevant code.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `question` | string | **yes** | — | Question about the codebase (e.g. `"How does authentication work?"`) |
| `max_context_tokens` | integer | no | `6000` | Maximum context tokens for answer generation |

**Returns:** Natural language answer with references to relevant functions and classes.

---

### Code Context

#### `get_function_context`
Get detailed context for a function: call relationships, parent class, related patterns.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `function_name` | string | **yes** | — | Function name |

**Returns:** Function signature, callers, callees, parent module/class, and related patterns.

---

#### `get_module_structure`
Get module structure: classes, functions, and dependencies.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `module_name` | string | **yes** | — | Module name (e.g. `src.caching.redis_cache`) |

**Returns:** Module's classes, functions, imports, and dependency relationships.

---

#### `get_call_graph`
Get function call graph showing caller/callee relationships.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `function_name` | string | **yes** | — | Function name |
| `depth` | integer | no | `2` | Traversal depth (1–4) |

**Returns:** Call graph as adjacency list with direction (calls/called_by) at specified depth.

---

#### `smart_context`
Automatically assemble optimal context for a task from multiple keywords.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `keywords` | string[] | **yes** | — | List of keywords to search |
| `current_file` | string | no | — | Currently active file path |
| `max_tokens` | integer | no | `4000` | Maximum token budget |

**Returns:** Combined context from code, patterns, and security information, optimized for token budget.

---

### Code Quality

#### `evaluate_code`
AI-powered code quality evaluation using Gemini Flash. Scores correctness, security, readability, and testability (1–5).

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | no | — | File path to evaluate |
| `code_snippet` | string | no | — | Code snippet to evaluate (alternative to `file_path`) |

At least one of `file_path` or `code_snippet` must be provided.

**Returns:** Quality scores (1–5) for each dimension with explanations and improvement suggestions.

---

#### `suggest_tests`
Auto-generate test skeletons based on knowledge graph analysis of function signatures, dependencies, and edge cases.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `function_name` | string | **yes** | — | Function to generate tests for |

**Returns:** Test skeleton code with mocked dependencies and edge case coverage.

---

#### `get_bug_hotspots`
Detect bug-prone code areas based on modification frequency and dependency count.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `top_k` | integer | no | `10` | Number of hotspots to return |

**Returns:** Ranked list of risky code locations with risk scores and contributing factors.

---

#### `assist_code`
KG-powered code modification suggestions. Analyzes call graph and similar code to generate improved versions.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target_function` | string | **yes** | — | Function to modify |
| `instruction` | string | **yes** | — | Modification instruction (e.g. `"add error handling"`, `"add type hints"`) |

**Returns:** Modified code with explanation of changes.

---

### Graph Management

#### `index_project`
Index an entire project into the knowledge graph. Parses all code files (.py/.js/.ts/.jsx/.tsx) and stores them in Neo4j with embeddings.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | **yes** | — | Root directory of the project |
| `no_embed` | boolean | no | `false` | Skip embedding generation (index structure only) |

**Returns:** Indexing summary with counts of functions, classes, and modules processed.

---

#### `evolve_ontology`
Knowledge graph self-healing. Detects and optionally fixes orphan nodes, god modules, circular dependencies, stale nodes, and schema drift.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `auto_fix` | boolean | no | `false` | Automatically delete orphans and archive stale nodes |

**Returns:** Report of detected issues and actions taken.

---

#### `get_graph_stats`
Get overall knowledge graph statistics (node counts, relationship counts, etc.).

No parameters.

**Returns:** Node/relationship counts by type, graph density, and health indicators.

---

#### `get_security_patterns`
Get security patterns and AI code vulnerability information from the graph.

No parameters.

**Returns:** Known security patterns, vulnerability types, and mitigation strategies.

---

#### `get_cache_stats`
Get cache performance statistics: hit rate, size, and performance metrics.

No parameters.

**Returns:** Cache hit/miss counts, hit rate percentage, and memory usage.

---

### Analytics & Observability

#### `get_analytics_summary`
Knowledge graph usage analytics: reference frequency, quality metrics, bias indicators.

No parameters.

**Returns:** Usage statistics, quality scores, and distribution analysis.

---

#### `get_top_referenced`
Get the most frequently referenced knowledge nodes.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | no | `20` | Maximum number of results |

**Returns:** Ranked list of nodes by reference count.

---

#### `get_recent_activity`
Get recently referenced or modified nodes.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `hours` | integer | no | `24` | Lookback period in hours |

**Returns:** Recently active nodes with timestamps and activity type.

---

#### `get_quality_report`
Knowledge graph quality report: bias detection, context accuracy, distribution balance.

No parameters.

**Returns:** Quality metrics with recommendations for improvement.

---

### Pattern Management

#### `promote_pattern`
Promote a verified pattern to GLOBAL namespace, making it referenceable across projects.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Node name to promote |

**Returns:** Confirmation of promotion with new global identifier.

---

#### `get_global_insights`
Get cross-project global insights: verified patterns, promotion candidates, anti-patterns.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | no | `10` | Maximum number of results |

**Returns:** Global patterns, candidates for promotion, and detected anti-patterns.

---

### Session & Context Sharing

#### `get_session_context`
Get cumulative context for the current conversation session: mentioned entities, intent flow, focus scope.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `reset` | boolean | no | `false` | Reset conversation state |

**Returns:** Session summary with entity mentions, intent history, and focus areas.

---

#### `get_shared_context`
Get context published by other sessions (bugs, active files, changes).

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_dir` | string | no | `""` | Filter by project directory |
| `keys` | string[] | no | — | Specific keys to retrieve (empty = all) |

**Returns:** Shared context entries from other sessions.

---

#### `publish_context`
Share context with other sessions: discovered bugs, active files, important changes.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `key` | string | **yes** | — | Context key (e.g. `"found_bug"`, `"active_file:path"`) |
| `value` | string | **yes** | — | Context value |

**Returns:** Confirmation of published context.

---

### Documentation

#### `generate_docs`
Auto-generate API documentation for a module or entire project using knowledge graph data. Includes Mermaid diagrams.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `module_name` | string | **yes** | — | Module name (`"*"` for entire project index) |
| `depth` | integer | no | `2` | Documentation depth: 1=overview, 2=detailed, 3=full |

**Returns:** Markdown documentation with function signatures, descriptions, and dependency diagrams.

---

## Error Handling

All tools return `types.TextContent` with a text field. On error, the text contains:

```
오류 발생: <ExceptionType> — 서버 로그를 확인하세요.
```

Detailed error information is logged server-side (structured JSON to stderr). Check the MCP server logs for full stack traces.

## Observability

- **Prometheus metrics**: Available at `http://localhost:9091/metrics` (configurable via `MCP_METRICS_PORT`)
- **Structured logging**: JSON logs to stderr, OpenTelemetry-compatible
- **Correlation IDs**: Each request gets a unique ID for tracing across logs
