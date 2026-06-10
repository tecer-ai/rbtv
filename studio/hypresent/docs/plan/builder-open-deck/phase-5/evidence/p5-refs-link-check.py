# p5-refs (B13) — deterministic plan-link check, conductor-executed.
# Verifies every path reference in the plan's deliverable docs resolves on disk and
# complies with the Plan Linking Standard:
#   internal (target inside the plan folder)  -> file-relative (resolves from the containing file's dir)
#   external (target outside the plan folder) -> project-root-relative (resolves from studio/hypresent)
#     (repo-root-relative refs to rbtv shared standards are reported as a tolerated variant, not a failure)
# Scope: plan, decisions, deliverables, learnings, structured-problem, specs/*, phase-*/*.task.md,
#        phase-*/evidence/*.md. Excluded: run-log.md + state-capsule.md (append-only state spine,
#        historical pre-rename paths are correct as records) and _dispatch-*.md (work-dir-relative
#        path maps by design).
import re, sys
from pathlib import Path

PLAN = Path(r"C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent\docs\plan\builder-open-deck")
HYP = PLAN.parents[2]          # studio/hypresent
RBTV = PLAN.parents[4]         # rbtv repo root

scope = [PLAN / "builder-open-deck-plan.md", PLAN / "decisions.md", PLAN / "deliverables.md",
         PLAN / "learnings.md", PLAN / "structured-problem-2026-06-09.md"]
scope += sorted((PLAN / "specs").glob("*.md"))
for ph in sorted(PLAN.glob("phase-*")):
    scope += sorted(ph.glob("*.task.md"))
    ev = ph / "evidence"
    if ev.is_dir():
        scope += sorted(ev.glob("*.md"))

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BACKTICK = re.compile(r"`([^`\n]+)`")
EXTS = (".md", ".py", ".js", ".html", ".json", ".txt", ".png", ".css", ".yaml", ".yml", ".pdf", ".log", ".csv")
SKIP_CHARS = set('*{}<>|()= "')

def candidates(text):
    out = []
    for m in MD_LINK.finditer(text):
        t = m.group(1)
        if not t.startswith(("http://", "https://", "mailto:", "#")):
            out.append(("mdlink", t.split("#")[0]))
    for m in BACKTICK.finditer(text):
        t = m.group(1).strip()
        if "/" not in t or t.startswith(("http", "~", "-", "$")) or any(c in SKIP_CHARS for c in t):
            continue
        if not (t.rstrip("/").endswith(EXTS) or t.endswith("/")):
            continue
        out.append(("backtick", t.rstrip()))
    return out

rows, broken, violations = [], [], []
for f in scope:
    rel_f = f.relative_to(PLAN).as_posix()
    text = f.read_text(encoding="utf-8", errors="replace")
    for kind, raw in candidates(text):
        t = raw.lstrip("!")  # embeds
        bases = [("file-relative", f.parent), ("plan-root", PLAN), ("project-root", HYP), ("repo-root", RBTV)]
        resolved = None
        for name, base in bases:
            p = (base / t).resolve() if not Path(t).is_absolute() else Path(t)
            if p.exists():
                resolved = (name, p)
                break
        if resolved is None:
            broken.append((rel_f, kind, raw))
            rows.append((rel_f, raw, "BROKEN", "resolves nowhere"))
            continue
        how, p = resolved
        internal = PLAN in p.parents or p == PLAN
        if internal and how in ("file-relative",):
            rows.append((rel_f, raw, "OK", "internal, file-relative"))
        elif internal and how in ("plan-root", "project-root", "repo-root"):
            # resolves only from a broader root -> not file-relative from the containing file
            violations.append((rel_f, raw, f"internal target but not file-relative (resolved via {how})"))
            rows.append((rel_f, raw, "VIOLATION", f"internal target, resolved via {how}"))
        elif not internal and how == "project-root":
            rows.append((rel_f, raw, "OK", "external, project-root-relative"))
        elif not internal and how == "repo-root":
            rows.append((rel_f, raw, "OK*", "external, rbtv-repo-root-relative (tolerated variant)"))
        elif not internal and how == "file-relative":
            violations.append((rel_f, raw, "external target written file-relative (should be project-root-relative)"))
            rows.append((rel_f, raw, "VIOLATION", "external target written file-relative"))
        else:
            violations.append((rel_f, raw, f"unclassified: how={how} internal={internal}"))
            rows.append((rel_f, raw, "VIOLATION", f"unclassified ({how})"))

print(f"FILES_SCANNED={len(scope)}")
print(f"REFS_CHECKED={len(rows)}")
print(f"BROKEN={len(broken)}")
print(f"VIOLATIONS={len(violations)}")
print()
for r in rows:
    if r[2] != "OK":
        print(" | ".join(r))
sys.exit(0 if not broken and not violations else 1)
