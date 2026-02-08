---
---

# Template: QA Documentation ([abbrev]-qa-[feature_name].md)

**Purpose:** Test cases, validation checklists, and test history for a feature.

---

## Expected Sections

```markdown
# QA: [Feature Name]

## For AI Agents

**Template reference:** This document was created from [`qa_documentation.md`](../../../system/founder/m6_mvp/qa_documentation.md). Agents MUST read the template before making updates.

---

**Feature #:** [Number from roadmap]
**Related Doc:** [[abbrev]-[feature_name].md]

---

## Test Cases

| # | Test Case | Steps | Expected Result | Status |
|---|-----------|-------|-----------------|--------|
| 1 | [Name] | [Steps to execute] | [Expected outcome] | [Pass/Fail/Pending] |

---

## Checklists

[Manual verification checklists]

### Functional Checklist

- [ ] [Check item 1]
- [ ] [Check item 2]

### Edge Cases Checklist

- [ ] [Edge case 1]
- [ ] [Edge case 2]

---

## Test Data

### Test Execution History

| Date | Tester | Version | Result | Notes |
|------|--------|---------|--------|-------|
| YYYY-MM-DD | [Name] | [Version] | [Pass/Fail/Partial] | [Observations] |

### Test Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| [Artifact name] | [Path or link] | [What it contains] |

### Reproduction Data

[Data, configurations, or setups used for testing that should be preserved for regression testing]

---

## Known Issues

[Documented issues discovered during testing]

| # | Issue | Severity | Status | Notes |
|---|-------|----------|--------|-------|
| 1 | [Description] | [Critical/High/Medium/Low] | [Open/Fixed/Won't Fix] | [Additional info] |

---

*Last updated: YYYY-MM-DD*
```

---

## Section Guidelines

| Section | Required | Notes |
|---------|----------|-------|
| Test Cases | Yes | Specific test scenarios |
| Checklists | Recommended | Manual verification items |
| Test Data | Yes | Record test executions and preserve test artifacts |
| Known Issues | Recommended | Track discovered issues |

---

## Test Data Guidelines

Test Data section serves three purposes:

1. **Test Execution History:** Record each test run with date, tester, results
2. **Test Artifacts:** Link to screenshots, logs, recordings
3. **Reproduction Data:** Document configurations needed to reproduce issues or rerun tests



