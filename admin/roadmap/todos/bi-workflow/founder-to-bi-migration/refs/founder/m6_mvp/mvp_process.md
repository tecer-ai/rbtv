---
---

# MVP Process

**Purpose:** Detailed process guide for Milestone 6 (MVP) of the founder module. Transforms validated concepts, brand identity, and market validation evidence into a minimum viable product usable by real customers.

**Goal:** Build and launch an MVP that delivers core value to real users, instrumented for learning, with quality sufficient for paying customers but scoped to the minimum feature set validated in prior milestones.

---

## Inputs

| Input | Source |
|-------|--------|
| Market validation evidence | M5 Market Validation (persevere decision) |
| Validated assumptions | M5 synthesis table |
| Pricing research | M5 Van Westendorp PSM |
| Top acquisition channels | M5 Bullseye Framework |
| PMF score and segment | M5 Sean Ellis Survey |
| Working prototype | M4 Prototypation |
| Brand identity | M3 Brand |
| Business concept | M1 Conception |

---

## Outputs

| Output | Format |
|--------|--------|
| User story map | Markdown document (`[project]/docs/founder/mvp/user_story_map.md`) |
| Feature documentation | Markdown documents per feature (`[project]/docs/product/[feature_name].md`) |
| System architecture | Markdown document (`[project]/docs/architecture/system_architecture.md`) with technology research, inline citations, and sources legend table |
| QA documentation | Markdown documents per feature (`[project]/docs/product/qa-[feature_name].md`) |
| Launch checklist | Markdown document (`[project]/docs/founder/mvp/launch_checklist.md`) |
| Deployed MVP | Live application |
| M6 Founder Diary | Markdown table (`[project]/docs/founder/mvp/m6_founder_diary.md`) |

---

## Steps Summary

| Step | Action | Framework | Output |
|------|--------|-----------|--------|
| 1 | Initialize M6 structure and define MVP scope | — | M6 folder structure, scope definition |
| 2 | Map user stories and prioritize features | User Story Mapping, INVEST Criteria | User story map |
| 3 | Prioritize MVP feature set | MoSCoW Prioritization | Prioritized backlog with Must/Should/Could/Won't |
| 4 | Define system architecture **[WEB RESEARCH MANDATORY]** | Technical Architecture Patterns | Architecture document |
| 5 | Build MVP in iterative sprints | Scrum/Agile, Feature Flags | Working application |
| 6 | Instrument analytics and error monitoring | Instrumentation/Analytics, Error Monitoring | Tracking implementation |
| 7 | Validate security and quality | OWASP Top 10, QA Documentation | Security audit, QA reports |
| 8 | Execute launch | Launch Checklist, Soft Launch Strategy | Deployed MVP, launch documentation |

---

## Step 1: Initialize M6 Structure

**Inputs:** M5 persevere decision, validated assumptions, pricing, channels

**Action:**
1. Create milestone folder: `[project]/docs/founder/mvp/`
2. Initialize founder diary from the template: [founder_diary.md](../templates/founder_diary.md)
3. Review M5 synthesis: which assumptions are validated? What is the PMF segment?
4. Define MVP scope boundaries:
   - What is the core value loop? (minimum actions a user must complete to get value)
   - What is explicitly out of scope for V1?
   - What is the target user segment? (from M5 Sean Ellis segmentation)
5. Review M5 pricing: what price point will the MVP launch at?
6. Review M5 channels: which 1-2 channels will drive initial users?
7. Update Session Status in m6_founder_diary.md

**Output:** M6 folder structure, clear MVP scope definition

**Framework Reference:** None (structural setup)

---

## Step 2: Map User Stories

**Inputs:** MVP scope, user flow map (M4), customer interviews (M5)

**Action:**
1. Create user story map with horizontal axis = user journey steps and vertical axis = priority
2. Write user stories following INVEST criteria:
   - **I**ndependent: each story delivers value alone
   - **N**egotiable: open to discussion on implementation
   - **V**aluable: delivers user or business value
   - **E**stimable: team can estimate effort
   - **S**mall: completable in one sprint
   - **T**estable: clear pass/fail criteria
3. Format: "As a [user], I want [goal] so that [benefit]"
4. Map stories to the core value loop defined in Step 1
5. Identify stories that must exist for MVP vs. nice-to-have
6. Save to `[project]/docs/founder/mvp/user_story_map.md`

**Output:** User story map with stories mapped to journey steps

**Framework Reference:** User Story Mapping, INVEST Criteria

---

## Step 3: Prioritize Features (MoSCoW)

**Inputs:** User story map, M5 validation evidence

**Action:**
1. Categorize every user story into MoSCoW priority:
   - **Must have:** MVP does not function without these. Core value loop requires them.
   - **Should have:** Important but MVP works without them. Add if time permits.
   - **Could have:** Desirable but low impact if omitted. First candidates to cut.
   - **Won't have (this time):** Explicitly deferred. Documented for post-MVP.
2. Validate Must-haves: does each Must-have directly support the core value loop?
3. Estimate effort for Must-haves: can they be built in the target timeline?
4. If Must-haves exceed capacity: challenge whether each is truly Must-have
5. Create feature documentation for each Must-have feature: read [feature_documentation.md](feature_documentation.md) (template)
6. Save feature docs to `[project]/docs/product/[feature_name].md`

**Output:** Prioritized backlog, feature documentation for Must-have features

**Framework Reference:** MoSCoW Prioritization

---

## Step 4: Define System Architecture

**Inputs:** Must-have features, technical constraints, team capabilities

**Action:**
1. Read system architecture template: [system_architecture.md](system_architecture.md) (template)
2. **Web research is MANDATORY for this step.** Read and follow [web-research/SKILL.md](../../../.cursor/skills/web-research/SKILL.md)
3. Research current best practices, tool comparisons, infrastructure pricing, security standards, and deprecated technologies
4. Define mandatory pre-PMF sections:
   - Tech stack with rationale for each layer
   - High-level architecture diagram (ASCII)
   - Core components and their responsibilities
   - Data architecture (entities, relationships, storage)
5. Make explicit architecture decisions and document tradeoffs:
   - Build vs. buy for each component
   - Monolith vs. microservices (monolith recommended pre-PMF)
   - Database choice and rationale
   - Hosting/deployment platform
6. Apply architecture principles for pre-PMF:
   - Optimize for speed of iteration, not scale
   - Choose boring technology over cutting-edge
   - Minimize infrastructure complexity
   - Plan for 10x current needs, not 1000x
7. Document all technology research sources per web-research skill requirements
8. Save to `[project]/docs/architecture/system_architecture.md`

**Output:** System architecture document with tech stack, diagram, components, data model, and sources legend

**Framework Reference:** Read [system_architecture.md](system_architecture.md) (template)

---

## Step 5: Build MVP in Sprints

**Inputs:** Prioritized backlog, architecture, feature documentation

**Action:**
1. Plan sprints (1-2 week cycles):
   - Sprint 1: Foundation (auth, database, core data model, deployment pipeline)
   - Sprint 2-N: Must-have features in priority order
   - Final sprint: Polish, bug fixes, launch preparation
2. Use feature flags for gradual rollout:
   - Wrap new features in flags
   - Enable for internal testing first
   - Enable for beta testers second
   - Enable for all users at launch
3. Per sprint:
   - Pick stories from Must-have backlog
   - Build, test, deploy to staging
   - Demo to stakeholders (even if solo founder)
   - Retrospect: what worked, what didn't, what to adjust
4. Set up CI/CD pipeline:
   - Automated testing on every commit
   - Automated deployment to staging
   - Manual promotion to production
   - Rollback capability

**Output:** Working application with Must-have features deployed

**Framework Reference:** Scrum/Agile, Feature Flags, CI/CD Pipeline

---

## Step 6: Instrument Analytics and Monitoring

**Inputs:** Deployed application, conversion goals from M5

**Action:**
1. Implement analytics tracking:
   - Core value loop events: user reaches each step of the value loop
   - Conversion events: signup, activation, first value moment, payment
   - Retention signals: return visits, feature usage frequency
   - Funnel tracking: where users drop off
2. Set up error monitoring:
   - Capture unhandled exceptions with stack traces
   - Track error rates by feature and user segment
   - Set up alerts for error spikes
   - Log user-facing errors for debugging
3. Define key metrics dashboard:
   - Daily active users
   - Activation rate (% who reach first value moment)
   - Retention (Day 1, Day 7, Day 30)
   - Conversion rate (free to paid, if applicable)
   - Revenue (MRR/ARR)
4. Validate tracking: manually walk through each instrumented flow and verify events fire

**Output:** Analytics tracking and error monitoring implemented and validated

**Framework Reference:** Instrumentation/Analytics, Error Monitoring

---

## Step 7: Validate Security and Quality

**Inputs:** Complete application

**Action:**
1. Conduct OWASP Top 10 security review:
   - Injection (SQL, NoSQL, OS command)
   - Broken authentication
   - Sensitive data exposure
   - XML external entities
   - Broken access control
   - Security misconfiguration
   - Cross-site scripting (XSS)
   - Insecure deserialization
   - Using components with known vulnerabilities
   - Insufficient logging and monitoring
2. Fix all Critical and High severity findings before launch
3. Create QA documentation per feature: read [qa_documentation.md](qa_documentation.md) (template)
4. Execute test cases:
   - Happy path for all Must-have features
   - Edge cases for payment and authentication flows
   - Cross-browser testing (Chrome, Safari, Firefox)
   - Mobile responsiveness testing
5. Save QA docs to `[project]/docs/product/qa-[feature_name].md`

**Output:** Security audit report, QA test results, all Critical/High issues resolved

**Framework Reference:** OWASP Top 10, read [qa_documentation.md](qa_documentation.md) (template)

---

## Step 8: Execute Launch

**Inputs:** Tested application, top channels from M5, pricing from M5

**Action:**
1. Complete launch checklist:
   - [ ] All Must-have features working in production
   - [ ] Analytics tracking validated in production
   - [ ] Error monitoring active with alerts configured
   - [ ] Payment processing tested with real transactions (sandbox first)
   - [ ] Customer support channel established (email minimum)
   - [ ] Legal requirements met (privacy policy, terms of service)
   - [ ] Domain and SSL configured
   - [ ] Backup and recovery tested
   - [ ] Rollback plan documented
2. Execute soft launch:
   - Week 1: Invite 5-10 users from M5 interview participants (warmest leads)
   - Week 2: Expand to 20-50 users via top channel
   - Week 3+: Open access, scale channel spend based on metrics
3. Monitor launch metrics daily:
   - Error rates, conversion rates, activation rates
   - Customer support volume and sentiment
   - Revenue and growth trajectory
4. Update project memo:
   - MVP section with completed work, tech stack, launch metrics
   - Open Questions with post-launch observations
   - Next Steps with growth priorities
5. Update m6_founder_diary.md with launch decisions and early metrics
6. Save launch checklist to `[project]/docs/founder/mvp/launch_checklist.md`

**Output:** Deployed MVP with paying users, launch documentation

**Framework Reference:** Launch Checklist, Soft Launch Strategy

---

## Success Criteria

MVP milestone is complete when:

- [ ] User story map exists with stories mapped to user journey
- [ ] Must-have features identified via MoSCoW and all built
- [ ] System architecture documented (tech stack, diagram, components, data model) with current best practices research, inline citations, and sources legend table
- [ ] Feature documentation exists for every Must-have feature
- [ ] CI/CD pipeline operational with automated testing
- [ ] Analytics tracking implemented and validated for core value loop
- [ ] Error monitoring active with alerts configured
- [ ] OWASP Top 10 security review completed with Critical/High issues resolved
- [ ] QA test cases executed for all Must-have features
- [ ] Soft launch executed with real users
- [ ] At least one paying customer (if revenue model applies)
- [ ] All technology choice and infrastructure claims have verified web sources (no training-data hallucinations)
- [ ] Project memo updated with MVP section and post-launch observations
- [ ] M6 founder diary has launch decisions and early metrics logged

---

## Post-MVP

After MVP launch, the founder module is complete. The project transitions from founder mode to product mode:

- Monitor metrics dashboard daily
- Iterate based on user feedback and analytics data
- Move from founder diary to product backlog management
- Revisit Should-have and Could-have features based on evidence
- Scale acquisition channels that proved effective in M5/M6

---

