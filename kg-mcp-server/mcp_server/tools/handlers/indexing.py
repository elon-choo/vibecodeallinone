"""Project indexing handler."""

import asyncio
import os
from pathlib import Path


async def index_project(reg, args: dict) -> str:
    project_path = args.get("project_path", "")
    no_embed = args.get("no_embed", False)

    if not os.path.isdir(project_path):
        return f"Error: '{project_path}' is not a valid directory"

    project_path = os.path.realpath(os.path.abspath(project_path))

    _cwd = os.path.realpath(os.getcwd())
    _home = os.path.realpath(os.path.expanduser("~"))
    if not (project_path.startswith(_cwd + os.sep) or project_path == _cwd
            or project_path.startswith(_home + os.sep) or project_path == _home):
        return f"Error: indexing is only allowed within the current working directory or user home. Got: '{project_path}'"

    _sensitive = {".ssh", ".gnupg", ".aws", ".config", ".kube", "etc", "private"}
    _parts = set(Path(project_path).parts)
    if _parts & _sensitive:
        return f"Error: refusing to index path containing sensitive directory: {_parts & _sensitive}"

    EXTS = {".py", ".js", ".ts", ".jsx", ".tsx"}
    EXCLUDES = {
        "node_modules", "__pycache__", ".git", "dist", "build",
        ".next", "venv", ".venv", ".tox", ".mypy_cache",
        ".pytest_cache", "coverage", ".turbo", ".cache",
    }

    files = []
    for root, dirs, fnames in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDES and not d.startswith(".")]
        for fn in fnames:
            if Path(fn).suffix in EXTS:
                files.append(os.path.join(root, fn))
    files.sort()

    if not files:
        return f"No indexable files found in {project_path}"

    loop = asyncio.get_event_loop()

    def _do_sync():
        synced = 0
        errors = 0
        total_functions = 0
        total_classes = 0
        error_details = []

        for fp in files:
            try:
                result = reg.write_back.sync_file(fp)
                if result.get("success"):
                    synced += 1
                    stats = result.get("stats", {})
                    total_functions += stats.get("functions", 0)
                    total_classes += stats.get("classes", 0)
                else:
                    errors += 1
                    if len(error_details) < 5:
                        rel = os.path.relpath(fp, project_path)
                        error_details.append(f"{rel}: {result.get('error', 'unknown')}")
            except Exception as e:
                errors += 1
                if len(error_details) < 5:
                    rel = os.path.relpath(fp, project_path)
                    error_details.append(f"{rel}: {e}")

        return synced, errors, total_functions, total_classes, error_details

    synced, errors, total_functions, total_classes, error_details = await loop.run_in_executor(None, _do_sync)

    embed_info = ""
    if not no_embed:
        def _do_embed():
            from mcp_server.pipeline.embedding_pipeline import EmbeddingPipeline
            ep = EmbeddingPipeline(reg.hybrid_search.driver)
            ep.create_vector_index()
            return ep.embed_all_nodes(batch_size=100)

        try:
            embed_stats = await loop.run_in_executor(None, _do_embed)
            embed_info = (
                f"\n\nEmbedding: {embed_stats.get('total_embedded', 0)} nodes embedded, "
                f"{embed_stats.get('total_errors', 0)} errors, "
                f"{embed_stats.get('elapsed_seconds', 0):.1f}s"
            )
        except Exception as e:
            embed_info = f"\n\nEmbedding failed: {e}"

    watch_info = ""
    try:
        import json as _json
        watched_path = os.path.expanduser("~/.claude/kg-watched-projects.json")
        if os.path.exists(watched_path):
            with open(watched_path, "r", encoding="utf-8") as f:
                watched = _json.load(f)
        else:
            watched = {"projects": [], "auto_detect": True, "exclude_patterns": list(EXCLUDES)}

        existing = {p["path"] for p in watched.get("projects", [])}
        if project_path not in existing:
            watched["projects"].append({
                "path": project_path,
                "enabled": True,
                "namespace": os.path.basename(project_path),
            })
            os.makedirs(os.path.dirname(watched_path), exist_ok=True)
            with open(watched_path, "w", encoding="utf-8") as f:
                _json.dump(watched, f, indent=2, ensure_ascii=False)
            watch_info = f"\nRegistered in watched-projects."
        else:
            watch_info = f"\nAlready in watched-projects."
    except Exception as e:
        watch_info = f"\nFailed to update watched-projects: {e}"

    lines = [
        f"# Project Indexed: {os.path.basename(project_path)}",
        f"",
        f"- Path: {project_path}",
        f"- Files scanned: {len(files)}",
        f"- Files synced: {synced}",
        f"- Sync errors: {errors}",
        f"- Functions: {total_functions}",
        f"- Classes: {total_classes}",
    ]

    if error_details:
        lines.append(f"\nFirst {len(error_details)} errors:")
        for ed in error_details:
            lines.append(f"  - {ed}")

    lines.append(embed_info)
    lines.append(watch_info)

    return "\n".join(lines)
