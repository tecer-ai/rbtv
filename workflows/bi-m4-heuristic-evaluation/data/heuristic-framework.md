# Heuristic Evaluation Framework

## Overview

Heuristic evaluation is a usability inspection method where evaluators examine an interface against established usability principles (heuristics). Nielsen's 10 usability heuristics are the industry standard for identifying usability problems.

**Purpose:** Identify usability issues early before user testing, when fixes are cheaper and faster.

**Context:** This framework is designed for founders evaluating their own prototypes/designs. It's not a replacement for user testing, but a complement that catches obvious issues before showing to users.

---

## Nielsen's 10 Usability Heuristics

### 1. Visibility of System Status

**Principle:** The system should always keep users informed about what is going on through appropriate feedback within reasonable time.

**Founder Examples:**
- Loading indicators when fetching data
- Progress bars for multi-step processes
- Confirmation messages after actions ("Saved successfully")
- Active state indicators (which tab/page is current)
- Form validation feedback (real-time or on submit)

**Common Violations:**
- No feedback after button clicks
- Long waits without indication
- Unclear whether action succeeded or failed

---

### 2. Match Between System and Real World

**Principle:** The system should speak the users' language, with words, phrases, and concepts familiar to the user, rather than system-oriented terms.

**Founder Examples:**
- Use customer terminology from JTBD interviews (not internal jargon)
- Icons that match real-world metaphors (trash can for delete)
- Natural ordering (chronological, alphabetical, by importance)
- Familiar patterns (e.g., shopping cart for e-commerce)

**Common Violations:**
- Technical error messages ("Error 500: Internal Server Error")
- Internal product names instead of customer-facing terms
- Unfamiliar icons without labels

---

### 3. User Control and Freedom

**Principle:** Users often choose system functions by mistake and need a clearly marked "emergency exit" to leave the unwanted state without having to go through an extended dialogue.

**Founder Examples:**
- Undo/Redo functionality
- Cancel buttons on forms
- Back navigation that works predictably
- Ability to exit multi-step flows
- Clear way to close modals/overlays

**Common Violations:**
- No way to cancel an action once started
- Irreversible destructive actions without confirmation
- Trapped in modal dialogs or flows

---

### 4. Consistency and Standards

**Principle:** Users should not have to wonder whether different words, situations, or actions mean the same thing. Follow platform conventions.

**Founder Examples:**
- Consistent button styles (primary vs. secondary)
- Consistent terminology (don't call it "Delete" in one place and "Remove" in another)
- Standard icon meanings (magnifying glass = search)
- Consistent navigation structure across pages
- Follow web conventions (logo links to home, links are underlined or colored)

**Common Violations:**
- Different UI patterns for the same action
- Inconsistent button placement
- Mixed terminology

---

### 5. Error Prevention

**Principle:** Even better than good error messages is a careful design that prevents a problem from occurring in the first place.

**Founder Examples:**
- Disable submit button until form is valid
- Confirmation dialogs for destructive actions
- Input constraints (date pickers instead of free text)
- Default values that make sense
- Clear constraints before user acts (character limits, file size limits)

**Common Violations:**
- Allowing invalid input without guidance
- No confirmation for destructive actions
- Unclear constraints that cause errors

---

### 6. Recognition Rather Than Recall

**Principle:** Minimize the user's memory load by making objects, actions, and options visible. The user should not have to remember information from one part of the dialogue to another.

**Founder Examples:**
- Show recent searches/entries
- Autocomplete suggestions
- Visible navigation (don't hide everything in hamburger menu)
- Inline help text for form fields
- Preview before committing (e.g., email preview before send)

**Common Violations:**
- Requiring users to remember codes or IDs
- Hidden navigation or features
- No context when resuming a task

---

### 7. Flexibility and Efficiency of Use

**Principle:** Accelerators—unseen by the novice user—may often speed up the interaction for the expert user such that the system can cater to both inexperienced and experienced users.

**Founder Examples:**
- Keyboard shortcuts for power users
- Bulk actions (select multiple items)
- Recently used items
- Customizable dashboards
- Quick filters or search

**Common Violations:**
- No shortcuts for repeated tasks
- Forcing all users through the same slow path
- No way to customize or optimize workflow

---

### 8. Aesthetic and Minimalist Design

**Principle:** Dialogues should not contain information that is irrelevant or rarely needed. Every extra unit of information competes with the relevant units of information.

**Founder Examples:**
- Focus on primary action per screen
- Remove unnecessary fields from forms
- Use progressive disclosure (show advanced options only when needed)
- Clear visual hierarchy (most important things stand out)
- White space to reduce cognitive load

**Common Violations:**
- Cluttered interfaces with too many options
- Equal visual weight for all elements
- Unnecessary information competing for attention

---

### 9. Help Users Recognize, Diagnose, and Recover from Errors

**Principle:** Error messages should be expressed in plain language (no codes), precisely indicate the problem, and constructively suggest a solution.

**Founder Examples:**
- "Email address must include @" instead of "Invalid input"
- "Password must be at least 8 characters" instead of "Password error"
- Suggest corrections ("Did you mean example@gmail.com?")
- Highlight the specific field with the error
- Provide actionable next steps

**Common Violations:**
- Generic error messages ("Something went wrong")
- Error codes without explanation
- No guidance on how to fix the error

---

### 10. Help and Documentation

**Principle:** Even though it's better if the system can be used without documentation, it may be necessary to provide help and documentation. Any such information should be easy to search, focused on the user's task, list concrete steps, and not be too large.

**Founder Examples:**
- Contextual help (tooltips, inline hints)
- FAQ addressing common questions
- Searchable help center
- Onboarding tours for new users
- Video tutorials for complex tasks

**Common Violations:**
- No help available
- Help documentation is generic or outdated
- Can't find help when needed

---

## Severity Rating Scale

Use this 0-4 scale to rate each violation:

| Rating | Severity | Description | Action Required |
|--------|----------|-------------|-----------------|
| 0 | Not a problem | Not a usability issue | None |
| 1 | Cosmetic | Doesn't need fixing unless extra time | Fix if easy |
| 2 | Minor | Low priority, fix if time allows | Schedule for future |
| 3 | Major | Important to fix, causes confusion or errors | Fix before launch |
| 4 | Catastrophic | Imperative to fix, blocks critical tasks | Fix immediately |

**Severity Factors:**
- **Frequency:** How often does this problem occur?
- **Impact:** When it occurs, how difficult is it for users to overcome?
- **Persistence:** Is it a one-time problem or does it keep bothering users?

---

## Evaluation Methodology

### Preparation
1. Define evaluation scope (which screens/flows to evaluate)
2. Gather design artifacts (wireframes, prototypes, live site)
3. Review Nielsen's 10 heuristics
4. Prepare documentation template

### Execution
1. Walk through each screen/flow systematically
2. For each element, ask: "Does this violate any heuristic?"
3. Document violations with:
   - Which heuristic is violated
   - Specific example/location
   - Why it's a problem
   - Severity rating (0-4)
4. Take screenshots or annotate designs

### Analysis
1. Group violations by heuristic
2. Prioritize by severity rating
3. Identify patterns (same heuristic violated repeatedly)
4. Generate recommendations with effort estimates

### Output
- Violations list (grouped by heuristic, sorted by severity)
- Prioritized recommendations
- Quick wins (high impact, low effort)
- Critical fixes (severity 3-4)

---

## Founder-Specific Guidance

**Time Investment:** 2-4 hours for a typical landing page or core flow. Don't aim for perfection—focus on severity 3-4 issues.

**When to Run:**
- After completing initial design (before implementation)
- After implementing prototype (before user testing)
- After major redesigns
- Before launch

**Limitations:**
- You're evaluating your own work (bias risk)
- Not a replacement for user testing
- May miss domain-specific usability issues
- Expert users may overlook novice problems

**Mitigation:**
- Use the heuristics as a checklist (forces systematic review)
- Imagine you're a first-time user
- Reference JTBD interviews for user perspective
- Get a co-founder or advisor to do a second pass
