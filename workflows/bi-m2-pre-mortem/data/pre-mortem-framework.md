# Pre-mortem Framework

**Purpose:** Use prospective hindsight to surface hidden risks that optimism bias normally suppresses. Imagine failure 12 months from now and explain why it happened.

---

## Core Concept

Gary Klein's prospective hindsight method reframes risk assessment. Instead of asking "what could go wrong?" (which triggers defensive optimism), you state as fact: "The project failed. It is 12 months from now. Why?"

This reframe gives psychological permission to voice doubts. Research shows prospective hindsight increases the ability to identify reasons for future outcomes by 30%.

---

## Seven Failure Categories

| Category | Failure Mode Focus |
|----------|-------------------|
| **Market** | Customers don't exist, don't care, or can't be reached |
| **Product** | Solution doesn't solve problem, is unusable, or not differentiated |
| **Team** | Missing skills, founder conflict, burnout, key person leaves |
| **Financial** | Revenue too low, costs too high, funding not secured, cash runs out |
| **Technical** | Can't build it, performance inadequate, integration fails, security breach |
| **Competitive** | Incumbent responds, new entrant captures market, open-source alternative |
| **Operational** | Regulatory block, legal issue, partner dependency fails, scaling bottleneck |

---

## Scoring Framework

### Likelihood Scale (1-5)

| Score | Meaning |
|-------|---------|
| 5 | Near certain — multiple signals already point to this |
| 4 | Probable — more likely than not given current evidence |
| 3 | Possible — could go either way, evidence mixed or absent |
| 2 | Unlikely — would require several things to go wrong |
| 1 | Remote — theoretically possible but requires extreme bad luck |

### Severity Scale (1-5)

| Score | Meaning |
|-------|---------|
| 5 | Fatal — project dies, no recovery path |
| 4 | Crippling — major pivot required, months of work lost |
| 3 | Serious — significant setback, recovery possible but expensive |
| 2 | Moderate — noticeable impact, can be managed with effort |
| 1 | Minor — inconvenience, normal course correction |

**Risk Score** = Likelihood × Severity (range 1-25)

---

## Mitigation Card Structure

For each top failure mode:

| Field | Description |
|-------|-------------|
| Failure Mode | One-sentence description from brainstorming |
| Root Cause | Underlying assumption, gap, or weakness |
| Mitigation Action | Concrete steps to reduce likelihood or severity |
| Early Warning Signal | Observable, measurable indicator with threshold |
| Trigger Response | What you do when signal fires |
| Owner | Who monitors and executes |
| Timeline | When action completes and when to first check signal |

---

## Kill Criteria Integration

Cross-reference each mitigation with Leap of Faith kill criteria:

1. If failure mode maps to existing kill criterion → align early warning signals
2. If failure mode reveals uncovered risk → propose new kill criterion
3. Every Severity 5 failure needs contingency plan (what if mitigation fails?)

---

## M2 Framework Integration

Pre-mortem consumes risks from all prior M2 frameworks:

| Framework | Risk Types Surfaced |
|-----------|-------------------|
| Leap of Faith | Kill criteria, high-impact assumptions |
| Assumption Mapping | "Test" quadrant items not yet validated |
| TAM/SAM/SOM | Market size gaps, segment risks |
| Unit Economics | Sensitivity points, break-even risks |
| TRL | Low-TRL components, technical unknowns |

---

## Pitfalls

1. **Running pre-mortem first** — MUST be last M2 framework
2. **Filtering during brainstorming** — capture everything, filter in ranking
3. **Vague failure modes** — reject "market risk"; demand specifics
4. **Treating as pessimism exercise** — goal is to surface and mitigate, not kill
5. **Ignoring early warning signals** — must assign owners and check-in dates

---

## Sources

- Gary Klein, "Performing a Project Premortem," HBR, September 2007
- Daniel Kahneman, *Thinking, Fast and Slow*, 2011
- David Bland & Alex Osterwalder, *Testing Business Ideas*, 2020
