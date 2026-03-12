"""Shared memory pool handlers."""

import os

from mcp_server.observability.session_tracker import get_current_session_id


async def get_shared_context(reg, args: dict) -> str:
    if not reg.shared_memory:
        return "SharedMemoryPool is not initialized."
    project_dir = args.get("project_dir", "")
    keys = args.get("keys")
    result = reg.shared_memory.get_context(project_dir, keys)
    if not result.get("success"):
        return f"조회 실패: {result.get('error')}"

    lines = [f"# Shared Context ({result['total']} entries)\n"]
    for entry in result.get("entries", []):
        lines.append(f"## [{entry['key']}]")
        lines.append(f"- Value: {entry['value']}")
        lines.append(f"- Session: {entry.get('session_id', 'N/A')}")
        lines.append(f"- Published: {entry.get('published_at', 'N/A')}")
        lines.append("")

    conflicts = result.get("conflicts", [])
    if conflicts:
        lines.append("## Conflicts Detected")
        for c in conflicts:
            lines.append(f"- {c['warning']}")

    return "\n".join(lines)


async def publish_context(reg, args: dict) -> str:
    if not reg.shared_memory:
        return "SharedMemoryPool is not initialized."
    key = args.get("key", "")
    value = args.get("value", "")
    session_id = get_current_session_id() or "unknown"
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")

    result = reg.shared_memory.publish(key, value, session_id, project_dir)
    if result.get("success"):
        return f"Published: [{key}] (TTL: {result['ttl_minutes']}min)"
    return f"Publish failed: {result.get('error')}"
