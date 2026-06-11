# Decisions — ui-bugfix-2026-06-11

> Append-only, worker-facing. Each entry = decision + rationale + scope. Workers (kimi) read this alongside their task file. Supersede by appending, never rewrite.

---

**D1 — Comment shortcut = `Ctrl+M`.** Replace `Ctrl+Alt+C` everywhere it binds the comment action (`runtime/js/shortcuts.js`, `app/js/main.js` document keydown, `app/js/shell/shortcuts-help.js` help table). Rationale: `Ctrl+Alt` == AltGr on the owner's Brazilian ABNT keyboard, consumed by the layout. `Ctrl+M` is AltGr-free, single-modifier, not Chrome-reserved. Scope: bug-1.

**D2 — Bug-6 = clarify the save dialog only (Option A).** Do NOT change the crossing architecture. Give the native save dialog shown on Editor↔Builder crossings a clear, contextual title (e.g. "Save before switching…") and surface a one-line message before it opens. Auto-open on the destination page already works via `?file=` — leave it. Scope: bug-6.

**D3 — Bug-4 topbar = basename + hover path; one indicator.** Show only the filename (basename) in the doc chip; expose the full path as a `title=` hover tooltip on the chip. Drop the inline "Saved to <full path>" status string (the chip's Saved/Unsaved state is the acknowledgement); keep `#shell-status` for transient errors only. Fix the basename split to handle Windows backslashes (`/[\\/]/`). Scope: bug-4.

**D4 — Bug-2 = sequential comment number by document order.** Every comment gets a sequential number derived from the document-order position of its anchor element (top-to-bottom), recomputed on each render so deletions renumber cleanly. Render the number on the in-deck marker badge AND in the panel thread header. This replaces the current `1 + replies.length` message-count badge. Scope: bug-2.

**D5 — Bugs 3 & 5 fixes are gated on a live repro.** The "mark-for-agent broke the UI / red comment" (bug-3) mechanism (unanchored vs highlight CSS; trigger) and the reply failure (bug-5) cannot be proven from source. Reproduce both on the real GSMM deck first; only then author their fix specs. Scope: bug-3, bug-5.

**D6 — Fix verification standard.** Each fix is verified by: (a) the relevant existing test(s) staying green, (b) a new test where the path was uncovered (bug-7 overwrite+blank, bug-8 inline-svg edit), and (c) a real-browser check on the GSMM deck for the UI-visible bugs. No fix is "done" on a kimi success message alone — disk + behavior decide. Scope: all.

**D7 — Bug-5 fix = Enter submits, Shift+Enter newline (live-confirmed).** The reply data path works; the failure is the popover composer (`app/js/shell/comment-composer.js`) treating plain Enter as a newline. Make plain Enter SUBMIT and Shift+Enter insert a newline, in the popover composer for ALL modes (new/reply/edit), keeping Ctrl+Enter as submit — matching the panel composer (`main.js:836`). Scope: bug-5. compoundable

**D9 — Executor switched kimi → codex; codex needs `$null \|` stdin EOF.** kimi hit a billing-cycle quota (403). Owner enabled codex CLI 0.137.0 (gpt-5.5, medium). Live-discovered: `codex exec` under the non-interactive PowerShell tool BLOCKS forever on "Reading additional input from stdin..." because stdin is a non-TTY pipe it tries to read. Fix: prefix every codex invocation with `$null \|` so stdin EOFs immediately (smoke then ran exit 0 in 39s). Installer availability block listed codex as absent, but `models/codex-cli/manual.md` is present on disk → live folder wins (logged). Invocation: `$null \| codex exec --cd "<hypresent>" --sandbox workspace-write -c approval_policy="never" --output-last-message "<file>" "<prompt>"`. Scope: all codex dispatches. compoundable

**D8 — Bug-3 fix = coalesce the comment-panel refresh; break not reproduced (per ADX-1).** A full live repro (toggle For-agents via label, save, reload, re-anchor, pin-click) showed NO break; the red box is the normal `.comment-thread-highlight` (pin click). The one real defect: every comment op triggers `refreshCommentPanel()` twice (the op handler's explicit call + the `dirty-changed` handler at `main.js:393-398`). Fix = make `refreshCommentPanel()` re-entrancy-safe (coalesce: if a refresh is in flight, queue exactly one more, drop extras) — ZERO behavior change, removes the overlapping-render race. This is best-effort for the unreproduced "UI broke"; surface to the owner with a request for exact repro steps. Do NOT remove any existing refresh trigger. Scope: bug-3. compoundable
