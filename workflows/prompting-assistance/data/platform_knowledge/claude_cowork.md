# Claude Cowork - Platform Interface Knowledge

**Platform:** Claude Desktop App (claude.com/download)  
**Feature:** Cowork  
**Purpose:** Enable AI agents to guide users through Cowork's agentic file-system interface — setup, task design, automation, plugins, and safety

---

## 1. Interface Overview

### Main Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Cowork sidebar entry | Left navigation | Launch Cowork mode from Desktop app |
| Folder selector | Session start | Choose which local folder Claude can access |
| Global Instructions | Settings → Cowork → Edit | Universal behavior applied to every session |
| Folder Instructions | Per-session config | Project-specific rules for the active folder |
| Task input / chat | Main area | Submit tasks, queue work, review plans |
| Plan preview | Inline (before execution) | Claude's proposed action list, awaiting approval |
| Subagent status | Inline | Parallel agents working on decomposed subtasks |
| Connectors panel | Settings → Connectors | Browse and connect external tools (Slack, Gmail, etc.) |
| Plugins panel | Customize menu | Install domain-specific skill bundles |
| /schedule command | Task input | Set up recurring automated tasks |

### Navigation Structure

1. **Folder selection** — Grant Claude access to a specific local folder; scopes all file read/write to that folder
2. **Session workspace** — Chat-style interface; queue multiple tasks; Claude works through them with or without supervision
3. **Settings → Cowork** — Manage Global Instructions, Folder Instructions, and linked Connectors
4. **Customize menu** — Install Plugins and create custom Skills
5. **Connectors browser** — Browse 50+ integrations; connect external data sources

---

## 2. Core Capabilities

### What Cowork Can Do

| Capability | Description |
|------------|-------------|
| Local file access | Read, create, edit, move, rename files in the granted folder |
| Agentic task execution | Plans multi-step tasks, executes with minimal prompting, loops user in on progress |
| Parallel subagents | Decomposes tasks into independent subtasks; runs them simultaneously |
| Scheduled tasks | `/schedule` command sets recurring autonomous runs (daily, weekly, monthly) |
| Connector access | Reads and writes to connected tools: Gmail, Slack, Google Drive, Notion, Asana, etc. |
| Plugin skills | Domain-specific capabilities bundled as slash commands and subagent configs |
| Global + Folder Instructions | Layered context: universal behavior + project-specific rules |
| Task queuing | Submit multiple tasks; Claude works through them in parallel |

### Primary Use Cases

- Organizing, renaming, and restructuring local file folders
- Processing batches of files (receipts, notes, drafts) into structured outputs
- Generating documents, reports, and presentations from scattered source material
- Competitive research across multiple sources simultaneously via subagents
- Recurring workflows: Monday briefings, Friday status reports, daily competitor tracking
- Multi-step connected workflows: ingest data → update spreadsheet → draft email

---

## 3. Integrated Tools

### Connectors

| Source | How to Access | Capabilities |
|--------|---------------|--------------|
| Gmail | Settings → Connectors → Gmail | Read emails, extract data, draft replies |
| Slack | Settings → Connectors → Slack | Read channels, summarize, categorize messages |
| Google Drive | Settings → Connectors → Google Drive | Read and write Drive files |
| Notion | Settings → Connectors → Notion | Read/write pages and databases |
| Asana | Settings → Connectors → Asana | Pull tasks, update status |
| 50+ others | Settings → Connectors → Browse connectors | Varies by integration |

### Sync Behavior

| Source | Sync Behavior |
|--------|---------------|
| Local folder | Direct file system access — always current |
| Gmail / Slack | Live pull at task execution time |
| Google Drive / Notion | Live pull at task execution time |
| Scheduled tasks | Connectors re-queried at each scheduled run |

---

## 4. User Actions

### Setting Up Global Instructions

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Open settings | Settings → Cowork |
| 2 | Edit instructions | Click "Edit" next to Global Instructions |
| 3 | Write behavior rules | Text area — role, output format, quality standards, uncertainty handling |
| 4 | Save | Click Save |

**Recommended Global Instructions structure:**
1. Who you are (role, context)
2. File-reading behavior ("Look for `_MANIFEST.md` first; load Tier 1 files")
3. Pre-execution behavior ("Show a plan before taking action; wait for approval")
4. Output defaults (format, quality bar)
5. Uncertainty handling ("If confidence < 80%, flag instead of guess")

### Starting a Cowork Session

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Open Cowork | Click "Cowork" in left sidebar |
| 2 | Select folder | Choose local folder to grant access |
| 3 | Review Folder Instructions | Add project-specific context if needed |
| 4 | Submit task | Type task in input field; define end state, constraints, uncertainty protocol |
| 5 | Review plan | Read Claude's proposed action list before approving |
| 6 | Approve or redirect | Confirm plan or correct before execution begins |

### Setting Up a Scheduled Task

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Type `/schedule` | Task input field |
| 2 | Follow Claude's prompts | Specify: task description, frequency, output location |
| 3 | Confirm schedule | Claude confirms scheduled task and next run time |

**Critical:** Scheduled tasks only run when the computer is awake and Claude Desktop is open.

### Installing Plugins

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Open Customize | Customize menu |
| 2 | Browse plugins | Plugin marketplace |
| 3 | Install | Select domain plugins matching your role |
| 4 | Stack | Install multiple; capabilities are composable across plugins |

### Creating a Custom Skill

| Step | Action | UI Element |
|------|--------|------------|
| 1 | Create `.md` file | New file in working folder or Customize menu upload |
| 2 | Structure content | Purpose → Inputs → Process → Output → Constraints |
| 3 | Save to folder | Claude reads it at session start |
| 4 | Invoke | "Run my [skill name] skill on [topic]" |

---

## 5. AI Agent Guidance

### How to Guide Users

| Task | Guidance Pattern |
|------|------------------|
| First-time setup | "Before your first session, set Global Instructions (Settings → Cowork → Edit). Define your role, file-reading order, output format, and uncertainty rules. This is your permanent baseline." |
| Context architecture | "Create a `_MANIFEST.md` in any project folder with 3 tiers: Tier 1 = source-of-truth files Claude reads first; Tier 2 = domain subfolders loaded on demand; Tier 3 = archived files Claude ignores unless asked." |
| Context files | "Create a `Claude Context` folder with three files: `about-me.md` (professional identity), `brand-voice.md` (tone and style), `working-style.md` (collaboration rules). These eliminate generic AI output." |
| Task prompting | "Don't tell Claude how to do the task — tell it what 'done' looks like. Include: end state, naming conventions, output artifacts, safety constraints, and what to do when uncertain." |
| Triggering subagents | "Add 'Spin up subagents to...' or 'Work on these in parallel using subagents' to your prompt. Best on Opus 4.6. Use for research, multi-source processing, or any task with independent subtasks." |
| Scheduling | "Type `/schedule` in any Cowork session. Claude walks you through setup. Best for Monday briefings, Friday reports, daily tracking. Requires Desktop to be open at run time." |
| Plugin stacking | "Install plugins matching your role. Capabilities are composable — use Data Analysis + Sales in a single task." |
| Custom skills | "Build a `.md` skill file for any workflow you repeat. Structure: Purpose, Inputs, Process, Output, Constraints. Invoke with 'Run my [skill name] skill on [topic]'." |

### When to Recommend Cowork

| Situation | Recommendation |
|-----------|----------------|
| User runs multi-step file tasks manually | "Cowork can plan and execute the full sequence — just define the end state." |
| User repeats same AI setup across sessions | "Build Global Instructions and context files once; never repeat setup again." |
| User processes batches of files | "Cowork can handle the full batch in one session using subagents for speed." |
| User wants recurring autonomous reports | "Use /schedule + connectors to pull live data and generate output automatically." |
| User gets inconsistent AI output | "The fix is context architecture — Manifest, Global Instructions, context files — not better prompting." |
| User has complex multi-source research | "Trigger subagents: four parallel agents researching four vendors takes 10 minutes, not 40." |

### Platform-Specific Instructions Format

Global Instructions and Folder Instructions accept plain text. Effective patterns:
- Role definition: "I am [name], a [role] who works with [clients/context]"
- File-reading order: "Look for `_MANIFEST.md` first. Load Tier 1 files. Load Tier 2 only when task touches that domain. Never load Tier 3 unless I ask."
- Pre-execution gate: "Show a brief plan before taking action. Wait for my approval before executing."
- Output defaults: "Default output format: .docx. Quality bar: client-ready without editing."
- Uncertainty protocol: "If confidence < 80%, flag and ask. Never guess on destructive actions."

---

## 6. Limitations and Constraints

### Platform Limitations

| Limitation | Description | Workaround |
|------------|-------------|------------|
| No cross-session memory | Cowork has no memory between sessions | Externalize everything to files: context files, skill files, log files |
| Desktop must be open for schedules | Scheduled tasks require awake machine + open Desktop | Plan schedules around working hours; Claude catches up on next open |
| Subagents consume more tokens | Parallel processing is compute-intensive | Use subagents for complex tasks where time savings justify cost |
| Folder access is explicit grant | Claude cannot access files outside granted folder | Scope granted folder deliberately; sensitive files in separate folders |
| Prompt injection risk | Malicious content in read files or websites can alter behavior | Avoid pointing Cowork at untrusted file sources or unknown URLs |
| Large context ≠ better output | Reading too many files adds noise, degrades output | Use `_MANIFEST.md` and deliberate context scoping |
| Deletion is possible | Claude can delete files if instructed (asks first by default) | Add "Don't delete anything" to Global Instructions unless deletions are intended |

### What Cowork Cannot Do

- Remember anything from a previous session without file-based continuity
- Run scheduled tasks when machine is asleep or Desktop is closed
- Access files outside the explicitly granted folder
- Guarantee safety against prompt injection (active development area)
- Share context across simultaneous independent sessions

---

## 7. Context Management

### How Context Works

| Component | Behavior |
|-----------|----------|
| Global Instructions | Loaded before everything — files, prompt, folder scan |
| Folder Instructions | Loaded after Global Instructions; project-specific additions |
| `_MANIFEST.md` | Guides which files Claude reads; prevents context noise |
| Context files (`about-me.md`, `brand-voice.md`, `working-style.md`) | Read at session start; persist across all tasks in session |
| Subagent context | Each subagent scoped to minimum context needed for its subtask |
| Session history | Available within a session; gone when session ends |

### Context Persistence

| Persists | Does Not Persist |
|----------|------------------|
| Global Instructions (settings) | Session conversation history |
| Folder Instructions (per folder) | Subagent intermediate results |
| Files in granted folder | Decisions made in previous sessions |
| Context files you maintain | Preferences not written to files |
| Skill files in folder | Anything not externalized to a file |

### Optimization Strategies

| Strategy | Implementation |
|----------|----------------|
| `_MANIFEST.md` tiering | Tier 1 (canonical) → Tier 2 (domain, on-demand) → Tier 3 (archive, ignored) |
| Deliberate context scoping | Instruct Claude in Global Instructions: load minimum context per task |
| Subagent scoping | "Give each subagent only the minimum context it needs for its specific subtask" |
| Batch related work | One session with five related tasks > five sessions with one task each |
| File-based continuity | Log decisions, outcomes, and preferences to files for cross-session persistence |
| Weekly context file refinement | Improve `about-me.md`, `brand-voice.md`, `working-style.md` based on output quality |

---

## 8. When to Use

### Ideal For

| Use Case | Why Cowork Helps |
|----------|------------------|
| Multi-step file tasks with defined end states | Claude plans, executes, and produces output autonomously |
| Batch processing (receipts, notes, drafts, research) | Subagents parallelize; single session handles full batch |
| Recurring autonomous workflows | `/schedule` + connectors runs workflows without prompting |
| Context-heavy work requiring consistent voice/standards | Context architecture eliminates generic output |
| Complex research across multiple sources | Parallel subagents reduce 40-minute tasks to 10 |
| Team standardization | Shared plugins and skill files enforce consistent output quality |

### Avoid For

| Use Case | Why Cowork Doesn't Help |
|----------|-------------------------|
| Single-turn questions needing no file access | Regular Claude chat is faster and cheaper |
| Tasks requiring access to files outside granted folder | Cannot cross folder boundaries |
| Unsupervised destructive operations on critical files | Requires established trust and explicit safety guards |
| Tasks with untrusted file or URL sources | Prompt injection risk |
| Highly exploratory work with no defined end state | Cowork works best when "done" is defined |

---

## 9. Common Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Leaving Global Instructions blank | Every session starts cold; Claude defaults to generic behavior | Set Global Instructions before first session; treat as permanent OS |
| Pointing Claude at entire Documents folder | Over-broad access; confidential files exposed | Grant access to specific working folders only |
| Skipping the plan approval step | Claude executes immediately; one misinterpreted word causes 20 minutes of wrong work | Add "Show plan, wait for approval" to Global Instructions |
| No uncertainty protocol | Claude guesses on ambiguous files or classifications | Add explicit uncertainty rules: flag, mark VERIFY, use /needs-review |
| Running many small sessions | Each session has startup cost; related context not shared | Batch related tasks into single sessions |
| Triggering subagents for simple tasks | Excess token consumption with no benefit | Use subagents only for tasks with independent parallel subtasks |
| Omitting `_MANIFEST.md` in large folders | Claude reads outdated drafts and superseded files; contradictory output | Add `_MANIFEST.md` to any folder with 10+ files |
| No context files (`about-me.md`, etc.) | Generic voice and output; must re-explain preferences every session | Create three context files; refine weekly |
| No "Don't delete" constraint | Deletion is possible; irreversible without backup | Add constraint to Global Instructions; back up before experimenting |
| Ignoring prompt injection risk | Malicious content in read files can alter Claude's behavior | Never point Cowork at untrusted file sources or unknown URLs |

---

## 10. Quality Checklist

Before starting production Cowork workflows:

- [ ] Global Instructions set — role, file-reading order, plan gate, output format, uncertainty protocol
- [ ] Three context files created — `about-me.md`, `brand-voice.md`, `working-style.md`
- [ ] `_MANIFEST.md` in place for any working folder with 10+ files
- [ ] Sensitive files excluded — confidential data in folders Cowork never accesses
- [ ] "Don't delete" constraint in Global Instructions (unless deletion is explicitly desired)
- [ ] At least one plan-approval run completed before autonomous unsupervised use
- [ ] Subagents tested on a non-critical task before use on production data
- [ ] Scheduled tasks verified to run correctly during working hours
- [ ] Connector access scoped to necessary integrations only

---

## 11. Visual Reference

### Context Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: Global Instructions (Settings → Cowork)       │
│  Role + file-reading order + plan gate + quality bar    │
├─────────────────────────────────────────────────────────┤
│  LAYER 2: Context Files (Claude Context folder)         │
│  about-me.md | brand-voice.md | working-style.md        │
├─────────────────────────────────────────────────────────┤
│  LAYER 3: Folder Instructions (per project folder)      │
│  Client name + project goals + terminology + deadlines  │
├─────────────────────────────────────────────────────────┤
│  LAYER 4: _MANIFEST.md (working folder)                 │
│  Tier 1: Canonical  |  Tier 2: Domain  |  Tier 3: Skip  │
├─────────────────────────────────────────────────────────┤
│  LAYER 5: Task Prompt                                   │
│  End state + constraints + uncertainty protocol         │
└─────────────────────────────────────────────────────────┘
```

### `_MANIFEST.md` Structure

```
# _MANIFEST.md

## Tier 1 — Canonical (read first, always)
- /brief.md — Project brief (source of truth)
- /brand-guidelines.md — Brand standards

## Tier 2 — Domain (load only when task touches this area)
- /pricing → Pricing models and rate cards
- /research → Competitor analysis

## Tier 3 — Archival (ignore unless explicitly requested)
- /archive → Old drafts and superseded versions
```

### Task Prompt Structure

```
End state:      [What does "done" look like?]
Constraints:    [Naming conventions, safety rules, format]
Artifacts:      [What files should be produced?]
Uncertainty:    [What to do when confidence is low?]
```

---

## 12. Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| Cowork announcement | https://claude.com/blog/cowork-research-preview |
| Download Desktop app | https://claude.com/download |
| Cowork for finance | https://claude.com/blog/cowork-plugins-finance |
| Cowork for enterprise teams | https://claude.com/blog/cowork-plugins-enterprise |
| Connectors overview | https://claude.com/connectors |
| Help Center — safety guidance | https://support.anthropic.com (search: Cowork safety) |

---

*Last updated: 2026-03-03*
