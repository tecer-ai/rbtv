---
name: 'bi-m4-design-context'
description: 'Bridge workflow: collect M1–M3 and User Flow & IA context, format for BMAD create-ux-design, invoke BMAD, integrate design output into project-memo'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m4/workflow.md
outputFolder: '{project-root}/_bmad-output/{project-name}/founder/m4-prototypation'
---

# M4 Design Context Bridge Workflow

**Goal:** Collect founder context from M1–M3 and User Flow & IA, format it for BMAD create-ux-design, run the BMAD workflow with prepared context, and integrate design output into project-memo. This bridge ensures Design Direction [D] has a single entry point with consistent inputs.

**Your Role:** YC mentor facilitating the handoff from RBTV M4 frameworks to BMAD UX design. Ensure context is complete and structured so the UX workflow can start without re-discovery.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After synthesis, update project-memo and instruct return to M4 milestone menu.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update project-memo after synthesis (Step 4)
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Run bridge from M4 Design Direction [D] | steps-c/step-01-init.md | design-context.md → BMAD output → project-memo update |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load project-memo, user-flow-ia.md, M1–M3 synthesis; verify prerequisites; determine artifact type/scope |
| 02 | Format Context | Build design brief / context document for BMAD create-ux-design |
| 02b | Update Config | Update BMAD config to use RBTV project folder |
| 03 | Invoke BMAD | Instruct run BMAD create-ux-design with prepared context |
| 03b | Restore Config | Restore BMAD config to defaults |
| 04 | Synthesis | Integrate BMAD output into project-memo; instruct return to M4 milestone menu |

---

## REFERRAL LOGIC

- **Entry:** User selects [D] Design Direction from M4 milestone menu → load this bridge workflow.
- **Exit:** After Step 4, update project-memo with Design Direction synthesis and instruct: "Return to M4 milestone menu and select [B] Back or next framework [B], [C], [H], [F]."

---

## BMAD WORKFLOW PATH

- **Path:** `{project-root}/_bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md`
- Step 3 instructs loading this workflow with the prepared design-context document as input.

---

## SUCCESS CRITERIA

Bridge is complete when:

1. Prerequisites verified (User Flow & IA complete; M1/M3 synthesis available)
2. design-context.md (or design-brief) created with artifact type, content hierarchy, CTA, brand refs
3. BMAD config updated to use RBTV project folder
4. User has run BMAD create-ux-design with that context
5. BMAD config restored to defaults
6. project-memo updated with Design Direction synthesis
7. User instructed to return to M4 milestone menu

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| ../bi-m4/workflow.md | Parent workflow; [D] routing | Step 01 |
| ../bi-m4-user-flow-ia/workflow.md | Source of user-flow-ia.md | Step 01 |
