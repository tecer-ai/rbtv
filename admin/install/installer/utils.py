def print_errors(errors: list) -> None:
    for err in errors:
        print(f"    Error: {err}")

def print_mcp_stats(stats: dict) -> None:
    if "reason" in stats:
        print(f"  Skipped ({stats['reason']})")
    else:
        print(f"  Added: {stats['added']}  |  Merged: {stats['merged']}")
        print_errors(stats.get("errors", []))
