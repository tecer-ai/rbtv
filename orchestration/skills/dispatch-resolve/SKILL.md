---
name: rbtv-dispatch-resolve
description: "Resolve the exact CLI-worker dispatch command — argv, binary, and the add-dir flag — from a NAMED launch profile, with the pinned-flag pre-flight run in the same call, instead of hand-composing the command line or the --add-dir flag. The conductor names the profile itself (no manifest records one — `launch_profile` was retired 2026-08-11). Refuses an absent work-target, a relative work-target, an unknown profile, a raw flag, an unknown effort level, and a pinned flag missing from the live --help."
---

# Dispatch Resolve

The conductor's pre-flight for a CLI-worker dispatch (`dispatch-wrapper.md` §5a, gate 5). **Manual
invocation is the contract** — no code path consumes this; the conductor calls it and reads the
result (owner ruling `d-r2-preflight-manual-plus-skill`, 2026-08-10, made permanent 2026-08-11).

⚠ **Read the capability doc's "What this lane does NOT give you" BEFORE relying on a resolved argv.**
Every shipped profile is a DAEMON SEAT profile — its argv assumes an assigned session id, a
daemon-host `--settings` path and the bwrap seat cage this lane does not resolve. There is no
manifest→profile mapping any more; every elected pair dispatches from its **package manual**, and the
pinned-flag gate for such a dispatch runs from that worker's delta Pre-flight (`routing.md` §4).

- **Capability directory:** `{rbtv_path}/orchestration/capabilities/dispatch-resolve/`
- **Read first, IN FULL:** `{rbtv_path}/orchestration/capabilities/dispatch-resolve/dispatch-resolve.md`
  — the refusals, the `{extra_dir}` opt-in, the honest remaining scope and the filed gaps.
- **Invoke** (CWD = `{rbtv_path}`):

```
node -e "const l=require('./orchestration/capabilities/dispatch-resolve');const c=l.loadProfiles('ignite/config/spawn-profiles.yaml');console.log(JSON.stringify(l.preflightDispatch(c,'<profile>',{addDir:'<ABSOLUTE work-target>',effort:'<low|medium|high>'}),null,2))"
```

Read `addDirResolved` on the result: `true` = the profile wrote the add-dir flag, `false` = you
still owe a hand-composed one. A refusal throws with a `code` (`E_*`) — do not dispatch; fix the
input or file the gap.
