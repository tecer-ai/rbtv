def convert_claude_agent_to_cursor(content: str) -> str:
    """Convert Claude agent frontmatter to Cursor agent frontmatter."""
    CLAUDE_ONLY_FIELDS = {
        "permissionMode", "tools", "hooks", "memory",
        "maxTurns", "mcpServers", "skills", "bypassPermissions",
    }
    if not content.startswith("---"):
        return content

    end = content.find("---", 3)
    if end == -1:
        return content

    front = content[3:end].strip()
    body = content[end + 3:]

    lines_out = []
    has_plan_mode = False

    for line in front.splitlines():
        stripped = line.strip()
        field_name = stripped.split(":")[0].strip() if ":" in stripped else ""

        if field_name == "permissionMode":
            val = stripped.split(":", 1)[1].strip().lower()
            if val == "plan":
                has_plan_mode = True
            continue

        if field_name in CLAUDE_ONLY_FIELDS:
            continue

        lines_out.append(line)

    if has_plan_mode:
        lines_out.append("readonly: true")

    return "---\n" + "\n".join(lines_out) + "\n---" + body
