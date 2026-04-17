def convert_claude_rule_to_mdc(content: str) -> str:
    """Convert Claude .md rule frontmatter to Cursor .mdc frontmatter."""
    if not content.startswith("---"):
        return content

    end = content.find("---", 3)
    if end == -1:
        return content

    front = content[3:end].strip()
    body = content[end + 3:]

    lines_out = []
    patterns = []
    in_paths_block = False

    for line in front.splitlines():
        stripped = line.strip()

        if stripped == "paths:":
            in_paths_block = True
            continue

        if in_paths_block:
            if stripped.startswith("- "):
                val = stripped[2:].strip().strip('"').strip("'")
                patterns.append(val)
                continue
            else:
                in_paths_block = False

        lines_out.append(line)

    if patterns:
        globs_str = ", ".join(patterns)
        lines_out.append(f'globs: "{globs_str}"')
        lines_out.append("alwaysApply: false")
    else:
        lines_out.append("alwaysApply: true")

    return "---\n" + "\n".join(lines_out) + "\n---" + body
