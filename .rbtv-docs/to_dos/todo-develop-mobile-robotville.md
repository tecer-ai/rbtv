# Mobile Robotville

**Status:** Concept  
**Target Platform:** Google Gemini Gems  
**Distribution:** Folder in robotville repository (future: ZIP download)

## Overview

Mobile Robotville is a portable version of Robotville optimized for Google Gemini Gems, enabling users to run the Founder module workflows in any environment with long context window support. Unlike BMAD's single agentic file approach, Mobile Robotville maintains a structured multi-file architecture focused on the founder frameworks.

## Core Concept

**Primary Goal:** Enable users to run Robotville's Founder module in Gemini Gems without Cursor dependency.

**Design Philosophy:** 
- Simplicity over completeness (minimal file count)
- Founder module as primary focus
- Manual sync with Cursor Robotville (source of truth)
- Inspired by BMAD's portability, but structured for framework-heavy workflows

## Architecture

### File Structure

```
mobile-robotville/
├── agents/           # Includes skills (merged for simplicity)
├── commands/         # Adapted for Gemini Gem environment
├── rules/            # Referenced in Gem instructions field
├── founder_process/  # Process documentation
├── founder_frameworks_m1/  # Milestone 1 frameworks
├── founder_frameworks_m2/  # Milestone 2 frameworks
├── founder_frameworks_m3/  # Milestone 3 frameworks
├── founder_frameworks_m4/  # Milestone 4 frameworks
├── founder_frameworks_m5/  # Milestone 5 frameworks
└── founder_frameworks_m6/  # Milestone 6 frameworks
```

### Components Included

| Component | Scope | Notes |
|-----------|-------|-------|
| **Agents** | Onboarder, DomCobb, user_profile settings | Onboarder generates user_profile.json for download/upload |
| **Commands** | All except git and compound | Adapted for Gem environment |
| **Rules** | All Cursor rules | Consolidated into single instructions file |
| **Skills** | All skills | Merged into agents folder |
| **Founder Frameworks** | All milestones (M1-M6) | Core value proposition |
| **Founder Process** | Process documentation | Workflow guidance |

### What's Excluded

- Git-specific commands
- Compound command (Cursor-specific)
- Cursor IDE integrations
- File system operations requiring Cursor tools

## Key Features

### 1. User Profile Persistence

**Problem:** Gemini Gems don't persist data between sessions.

**Solution:** 
- Onboarder agent completes onboarding process
- Generates `user_profile.json` file
- Instructs user to download JSON
- User uploads JSON to new Gem chat sessions
- Profile data available across all sessions

### 2. Context Window Management

**Monitoring:**
- Agent actively monitors token count usage
- Alert threshold: 40% context window capacity
- Proactive handoff recommendations

**Handoff Process:**
- Agent produces comprehensive handoff markdown (up to 20k characters)
- Handoff document includes:
  - Key decisions made
  - Discoveries and insights
  - Current state and progress
  - Next steps and recommendations
  - Critical context for continuation
- User downloads handoff markdown
- User starts new Gem chat and uploads handoff
- Seamless continuation with minimal context loss

### 3. Working Memory Management

**Challenge:** Founder module produces artifacts (documents, frameworks, decisions) that need persistence.

**Solution:**
- Agent instructs user to download produced documents
- User uploads documents to Gem as new files when needed
- Agent references uploaded documents in subsequent work
- Maintains project continuity across framework completions

**Workflow:**
- Complete framework → Agent produces artifact
- Agent instructs download
- Framework completion → Agent suggests new chat
- User starts fresh chat with relevant artifacts uploaded

### 4. Framework-Centric Sessions

**Session Management:**
- Each framework completion = natural session boundary
- Agent instructs user to start new chat after framework completion
- Prevents context bloat from accumulating across milestones
- Fresh context for each major framework

## Translation Map

**Purpose:** Instructions for AI agents to translate Cursor Robotville files (source of truth) into Mobile Robotville format.

**Location:** `docs/future_developments/mobile-robotville-translation-map.md` (to be created)

**Translation Requirements:**
- Remove Cursor-specific tool calls
- Adapt file system operations for Gem environment
- Convert IDE integrations to manual instructions
- Preserve core logic and frameworks intact
- Update agent invocation patterns for Gem context
- Simplify multi-file structures where possible

**Key Translations:**

| Cursor Element | Mobile Translation |
|----------------|-------------------|
| File read/write tools | Manual download/upload instructions |
| Git operations | Removed entirely |
| Cursor commands | Adapted or removed |
| IDE-specific features | Manual alternatives |
| Tool invocations | Gem-native equivalents |
| Context management | Explicit handoff protocols |

## Development Priorities

### Phase 1: Core Structure
- [ ] Create folder structure in robotville repo
- [ ] Document translation map (AI agent instructions)
- [ ] Identify BMAD patterns to adopt (GitHub reference needed)

### Phase 2: Content Translation
- [ ] Translate founder frameworks (all milestones)
- [ ] Adapt agents (onboarder, domcobb, user_profile)
- [ ] Convert commands (exclude git, compound)
- [ ] Consolidate rules into instructions file

### Phase 3: Gem-Specific Features
- [ ] Implement context monitoring
- [ ] Design handoff markdown template
- [ ] Create working memory management instructions
- [ ] Test user profile persistence workflow

### Phase 4: Distribution
- [ ] Package as ZIP for download
- [ ] Create installation instructions
- [ ] Document update/sync process

## Open Questions

**To be resolved during development:**

1. **Simplicity vs Functionality Balance**
   - How minimal can file structure be while maintaining framework completeness?
   - Which components can be merged without losing clarity?

2. **BMAD Inspiration**
   - What specific patterns from BMAD GitHub should be adopted?
   - How does BMAD handle context management in single-file format?

3. **Gemini Gem Capabilities**
   - What integrated tools are available (email, etc.)?
   - How to leverage Gem-native features?
   - What are actual context window limits?

## References

- **BMAD GitHub:** (URL to be added - single agentic file inspiration)
- **Cursor Robotville:** Source of truth for all content
- **Lovable System Prompt:** Prompt engineering structure reference
- **Translation Map:** (To be created) AI agent instructions for Cursor → Mobile conversion

## Success Criteria

- [ ] User can run complete Founder module workflow in Gemini Gem
- [ ] Onboarding produces persistent user profile
- [ ] Context handoffs preserve critical information
- [ ] Framework artifacts persist across sessions
- [ ] Manual sync process is clear and maintainable
- [ ] File count minimized without sacrificing functionality

---

*Last updated: 2026-01-31*
