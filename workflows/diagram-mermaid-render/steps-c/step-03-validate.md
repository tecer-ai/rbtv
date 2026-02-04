---
stepNumber: 3
stepName: 'validate'
nextStepFile: ./step-04-update.md
---

# Step 03: Validate Clarity

**Progress: Step 3 of 4** — Next: Update Markdown

---

## STEP GOAL

Validate visual clarity of complex diagrams (5+ nodes) and optimize layouts with crossing arrows.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Diagram Conversion Specialist with layout optimization expertise. Assess visual clarity objectively.

### Step-Specific Rules

- Only validate diagrams identified as having 5+ nodes
- Use browser MCP to inspect rendered PNG files
- Count crossing arrows — threshold is 2+ for optimization
- Apply optimization techniques in priority order
- Maximum 3 optimization attempts per diagram
- Preserve diagram fidelity (all nodes, edges, labels)

---

## MANDATORY SEQUENCE

### 1. Report Validation Plan

If no diagrams require validation:
```
No diagrams require visual validation (all have < 5 nodes).
Proceeding to update Markdown.
```
Auto-continue to step-04.

Otherwise:
```
Validating {N} diagram(s) with 5+ nodes:

| Diagram | Nodes | Status |
|---------|-------|--------|
| diagram_{NN}.png | {count} | Pending |
...
```

### 2. Validate Each Complex Diagram

For each diagram with 5+ nodes:

#### 2a. Open in Browser

1. Convert path to absolute
2. Construct file URL: `file:///[absolute_path]`
3. Navigate using `browser_navigate`

**Critical:** Do NOT prepend `https://` and do NOT URL-encode the path.

#### 2b. Assess Complexity

Before optimizing, check if diagram should be split:

| Condition | Recommendation |
|-----------|----------------|
| 2+ subgraphs | Recommend splitting into separate diagrams |
| Multiple distinct concepts | Recommend splitting by concept |
| Mixed orientations | Recommend standardizing flow direction |

If splitting recommended, present to user and HALT for decision.

#### 2c. Count Crossing Arrows

Take screenshot and visually inspect:
- Count edge intersections (crossing arrows)
- Document crossing locations

| Crossings | Action |
|-----------|--------|
| 0-1 | Pass — diagram is clear |
| 2+ | Optimize — apply layout techniques |

#### 2d. Optimize Layout (If Needed)

Apply techniques in priority order until crossings ≤ 1:

| # | Technique | Description |
|---|-----------|-------------|
| 0 | Split into multiple diagrams | Separate distinct concepts |
| 1 | Change flow direction | `flowchart TD` → `flowchart LR` |
| 2 | Reorder node definitions | Define nodes in visual order |
| 3 | Group with subgraphs | Cluster related nodes |
| 4 | Add invisible nodes | Spacer nodes for layout control |
| 5 | Split long edges | Intermediate nodes on long edges |
| 6 | Use link styles | Link lengths for edge routing |
| 7 | Rearrange edge declarations | Group related edges |
| 8 | Reduce back-edges | Minimize against-flow edges |

**Optimization Loop:**

1. Apply one technique
2. Re-render diagram with mmdc
3. Re-inspect with browser
4. If crossings > 1 and attempts < 3, try next technique
5. Stop when crossings ≤ 1 OR 3 attempts made

#### 2e. Fidelity Check

After optimization, verify:
- All nodes present
- All edges preserved (source → target unchanged)
- Edge labels unchanged
- Subgraph groupings match logical groupings

**If fidelity broken:** Revert to original and report.

#### 2f. Report Result

```
Diagram {NN}: {Pass/Optimized/Failed}
- Original crossings: {count}
- Final crossings: {count}
- Techniques applied: {list or 'none'}
```

### 3. Validation Summary

```
Validation Complete:
- Passed without changes: {count}
- Optimized successfully: {count}
- Could not optimize (>1 crossing remaining): {count}
- Recommended for splitting: {count}

{If any recommended for splitting, list them}
```

### 4. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to update Markdown (step-04)
- **[O] Optimize More** — Continue optimizing a specific diagram
- **[S] Split Diagram** — Create separate diagrams from a complex one
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## CROSSING ARROW EXAMPLES

**Clear (0-1 crossings):**
```
A → B → C
↓       ↓
D → → → E
```

**Unclear (2+ crossings):**
```
A → → → C
↓ ↘ ↗ ↓
B ← ← ← D
```

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Record final state of all diagrams (original or optimized)
2. Load `./step-04-update.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All complex diagrams inspected visually
- Crossing arrows counted accurately
- Optimization attempted where needed (max 3 tries)
- Fidelity verified after optimization
- Clear report of results
- Menu presented with explicit HALT

❌ **FAILURE:**
- Skipping visual inspection
- Not counting crossing arrows
- Breaking diagram fidelity during optimization
- Exceeding 3 optimization attempts
- Proceeding to next step without user selecting Continue
