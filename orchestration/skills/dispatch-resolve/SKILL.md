---
name: rbtv-dispatch-resolve
description: "Resolve the exact CLI-worker dispatch command — argv, binary, and the add-dir flag — from a NAMED launch profile, with the pinned-flag pre-flight run in the same call. Use BEFORE packaging a dispatch to any CLI worker whose (model, variant) records a `launch_profile`, instead of hand-composing the command line or the --add-dir flag. Refuses a seat-bound profile, an absent work-target, a relative work-target, an unknown profile, a raw flag, an unknown effort level, and a pinned flag missing from the live --help."
---

# Dispatch Resolve

The conductor's pre-flight for a CLI-worker dispatch (`dispatch-wrapper.md` §5a, gate 5). **Manual
invocation is the contract** — no code path consumes this; the conductor calls it and reads the
result (owner ruling `d-r2-preflight-manual-plus-skill`, 2026-08-10).

- **Capability directory:** `{rbtv_path}/orchestration/capabilities/dispatch-resolve/`
- **Read first, IN FULL:** `{rbtv_path}/orchestration/capabilities/dispatch-resolve/dispatch-resolve.md`
  — the refusals, the `{extra_dir}` opt-in, current coverage (2 of 11 pairs) and the filed gaps.
- **Invoke** (CWD = `{rbtv_path}`):

```
node -e "const l=require('./orchestration/capabilities/dispatch-resolve');const c=l.loadProfiles('ignite/config/spawn-profiles.yaml');console.log(JSON.stringify(l.preflightDispatch(c,'<profile>',{addDir:'<ABSOLUTE work-target>',effort:'<low|medium|high>'}),null,2))"
```

Read `addDirResolved` on the result: `true` = the profile wrote the add-dir flag, `false` = you
still owe a hand-composed one. A refusal throws with a `code` (`E_*`) — do not dispatch; fix the
input or file the gap.
