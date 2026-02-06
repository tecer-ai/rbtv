# Platform Interface Knowledge

**Status:** Concept  
**Category:** Knowledge Base (not AI model documentation, not prompting technique)  
**Purpose:** Enable AI agents to understand platform interfaces, capabilities, and integrated tools

## Overview

Documentation of platform user interfaces, capabilities, and integrated tools so AI agents can effectively help users build and work within these environments. Inspired by Lovable's system prompt approach of describing its own interface to enable better AI assistance.

## Concept

**Problem:** AI agents often lack understanding of:
- Platform-specific UI elements and workflows
- Available integrated tools (email, calendar, etc.)
- Platform capabilities and limitations
- How to guide users through platform-specific actions

**Solution:** Create comprehensive platform interface documentation that describes:
- UI structure and navigation
- Available actions and features
- Integrated tools and how to use them
- Platform-specific best practices
- Limitations and constraints

**Key Insight from Lovable:** Lovable includes detailed descriptions of its own interface in its system prompt, enabling the AI to guide users effectively through the platform. This is neither AI model documentation nor a prompting technique—it's interface knowledge.

## Target Platforms

### 1. Google Gemini Gems

**Documentation Scope:**
- Gem creation and configuration interface
- Instructions field and how it works
- File upload/download mechanisms
- Integrated tools (email, etc.)
- Context window behavior
- Multi-turn conversation patterns
- Limitations and constraints

**Why Important:**
- Mobile Robotville will run on Gems
- Users need guidance on Gem-specific workflows
- Integrated tools offer unique capabilities
- Context management is critical

### 2. Cursor IDE

**Documentation Scope:**
- Editor interface and features
- Agent/Composer modes
- Rules, skills, commands, agents system
- File operations and navigation
- Terminal integration
- Git integration
- Context window management
- Multi-file editing patterns

**Why Important:**
- Robotville's primary platform
- Users need help leveraging Cursor features
- Agent needs to understand its own environment
- Optimize workflows for Cursor capabilities

### 3. Claude Projects

**Documentation Scope:**
- Project creation and organization
- Custom instructions
- Knowledge base integration
- File attachments
- Conversation management
- Project-specific context
- Collaboration features

**Why Important:**
- Alternative platform for Robotville workflows
- Different context management model
- Unique knowledge base capabilities
- Project-level persistence

## Documentation Structure

### Per-Platform Template

Each platform documentation should include:

#### 1. Interface Overview
- Main UI components
- Navigation structure
- Key interaction patterns
- Visual layout description

#### 2. Core Capabilities
- What the platform can do
- Primary use cases
- Unique features
- Performance characteristics

#### 3. Integrated Tools
- Available integrations (email, calendar, etc.)
- How to invoke/use each tool
- Tool capabilities and limitations
- Authentication and permissions

#### 4. User Actions
- How users perform common tasks
- Step-by-step workflows
- UI element locations
- Keyboard shortcuts

#### 5. AI Agent Guidance
- How AI should guide users
- Platform-specific instructions format
- Best practices for assistance
- Common pitfalls to avoid

#### 6. Limitations and Constraints
- What the platform cannot do
- Known issues or quirks
- Workarounds for limitations
- When to use alternative approaches

#### 7. Context Management
- How context works on this platform
- Context window size/limits
- Persistence behavior
- Context optimization strategies

## Knowledge Base Location

**Proposed Location:** `system/ai_pro/platform_knowledge/`

**Structure:**
```
system/ai_pro/platform_knowledge/
├── gemini_gems.md
├── cursor_ide.md
└── claude_projects.md
```

**Rationale:**
- Not an AI model (like `ai_models/claude.md`)
- Not a prompting technique (like `prompting_techniques/xml_tag_structure.md`)
- Platform-specific knowledge for AI agents
- Parallel to existing `ai_models/` and `prompting_techniques/` folders

## Content Sources

### 1. Official Documentation
- Platform user guides
- API documentation
- Feature announcements
- Release notes

### 2. System Prompt Analysis
- Lovable leaked prompt (reference: https://dfolloni.substack.com/p/o-system-prompt-do-lovable-vazou)
- Other leaked prompts from similar platforms
- How they describe their own interfaces

### 3. User Experience Research
- Direct platform usage
- Screenshot analysis
- Workflow documentation
- User feedback

### 4. Integration Documentation
- Integrated tool APIs
- Authentication flows
- Permission models
- Usage examples

## Lovable System Prompt Reference

**Key Learnings from Lovable Approach:**

1. **Interface Description:**
   - Describes left panel (chat) and right panel (preview)
   - Explains how user interacts with each
   - Clarifies what AI can see/control

2. **Technology Stack:**
   - Explicitly states supported frameworks
   - Lists what is NOT supported
   - Sets clear boundaries

3. **Workflow Guidance:**
   - Describes step-by-step processes
   - Explains when to use which features
   - Provides decision-making criteria

4. **Output Format:**
   - Specifies how to format responses
   - Defines custom UI components
   - Sets communication style

5. **Examples:**
   - Shows input → output → reasoning
   - Demonstrates expected behavior
   - Clarifies ambiguous scenarios

**Application to Robotville:**
- Apply same structure to platform knowledge docs
- Describe interfaces from AI agent perspective
- Include decision-making guidance
- Provide concrete examples

## Development Priorities

### Phase 1: Structure Definition
- [x] Finalize documentation template
- [x] Create folder structure in `system/ai_pro/platform_knowledge/`
- [ ] Define content standards

### Phase 2: Gemini Gems Documentation
- [ ] Document Gem interface
- [ ] List integrated tools and usage
- [ ] Describe context management
- [ ] Add workflow examples

### Phase 3: Cursor IDE Documentation
- [ ] Document Cursor interface
- [ ] Explain rules/skills/commands system
- [ ] Describe agent capabilities
- [ ] Add optimization guidance

### Phase 4: Claude Projects Documentation
- [x] Document Projects interface
- [x] Explain knowledge base system
- [x] Describe project organization
- [ ] Add collaboration patterns

### Phase 5: Integration
- [ ] Reference from relevant agents
- [ ] Update Mobile Robotville to use Gems knowledge
- [ ] Create cross-platform comparison guide
- [ ] Validate with user testing

## Success Criteria

- [ ] AI agents can accurately guide users through platform-specific tasks
- [ ] Documentation covers all major platform features
- [ ] Integrated tools are well-documented with usage examples
- [ ] Clear distinction from AI model and prompting technique docs
- [ ] Agents reference platform knowledge when helping users
- [ ] Users report improved AI guidance on platform-specific actions

## Open Questions

**To be resolved during development:**

1. **Documentation Depth:**
   - How detailed should UI descriptions be?
   - Balance between completeness and maintainability?
   - When to reference official docs vs inline explanation?

2. **Update Frequency:**
   - How to keep docs current as platforms evolve?
   - Versioning strategy?
   - Change notification process?

3. **Agent Integration:**
   - How do agents know when to reference platform knowledge?
   - Auto-load vs on-demand?
   - Context window impact?

## References

- **Lovable System Prompt Analysis:** https://dfolloni.substack.com/p/o-system-prompt-do-lovable-vazou
- **Prompt Engineering Structure:** 6-component framework (Role, Task, Instructions, Output Format, Examples, Input)
- **Existing Knowledge Bases:** `system/ai_pro/prompting/ai_models/`, `system/ai_pro/prompting/prompting_techniques/`

## Notes

- This is NOT about how to prompt AI models
- This IS about how to use platform interfaces
- Focus on actionable guidance for AI agents
- Prioritize integrated tools documentation (unique value)
- Learn from Lovable's self-description approach
- Keep separate from model capabilities documentation

---

*Last updated: 2026-01-31*
