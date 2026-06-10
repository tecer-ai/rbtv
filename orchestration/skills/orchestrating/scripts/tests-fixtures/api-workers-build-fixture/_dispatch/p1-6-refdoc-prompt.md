# DISPATCH — p1-6 (kimi, no-thinking) — CREATE `docs/routing-matrix-reference.md`

## You are a NON-REASONING bounded executor — MECHANICAL HARVEST ONLY
This is a translate-and-reframe task. Harvest the inlined Portuguese source into an English reference doc. Do NOT add new analysis, do NOT invent data, do NOT re-rank or editorialize. Translate faithfully + restructure as instructed. If something is genuinely ambiguous, STOP and return `status: DOUBT_ESCALATED`.

## Work-dir
Your work-dir is the rbtv repo root (passed via `--work-dir`). The output path below is relative to it.

## Allowlist — your ENTIRE write universe
- ✚ CREATE: `orchestration/docs/routing-matrix-reference.md`

Create NOTHING else. NEVER write scratch/log/summary files anywhere (stray-file ban). Do NOT read other files — the source is inlined below.

## Forbidden ops
- NO `git`. NO writes outside the allowlist. NO network. NO subagents.

## Goal
CREATE `orchestration/docs/routing-matrix-reference.md` — the harvested AI-provider routing matrix as **English REFERENCE DATA** for the conductor's within-tier tiebreaking. Translate the inlined Portuguese source to English, preserve every per-provider table (models, context, prices, modes, web capability) and the quick-decision matrix.

## Required output structure
1. **Header (write this verbatim at the top):**
   > **Reference data — NOT a router.** This is a within-tier TIEBREAKER the conductor may consult; it is NEVER the master routing cut (boundedness-first stays the cut, per `cards/routing.md`). Model ids and prices are 2026 estimates harvested from a prior research doc — **re-verify against provider docs before relying on any specific id/price.**
2. **Per-provider sections** for: Anthropic Claude, DeepSeek, Kimi, Gemini, OpenAI, Cohere, Manus, Qwen — each with its model table (translated to English) + a 1–2 line capability summary. Keep prices/context/modes exactly as in the source.
3. **OpenAI note (add to the OpenAI section):** "Routed via the `codex` CLI (code execution) in this workspace — NOT built as an API chat worker (dropped per build decision D1). Listed here as reference only."
4. **Quick-decision matrix** (translate the "Matriz de Decisão Rápida" table to English).
5. **Source citations** — keep the provider doc URLs from the source's references section (one line each).

## [INLINED] Source to harvest — manus-orchestation-scripts/docs/routing_matrix.md (Portuguese; translate faithfully)
```markdown
# Matriz de Roteamento de Agentes IA - 2026

## 1. Anthropic Claude
| Modelo | Contexto | Max Output | Preço (entrada/saída) | Thinking | Knowledge Cutoff |
| Claude Opus 4.8 | 1M tokens | 128k | $5/$25 por MTok | Adaptive | Jan 2026 |
| Claude Sonnet 4.6 | 1M tokens | 64k | $3/$15 por MTok | Extended | Aug 2025 |
| Claude Haiku 4.5 | 200k tokens | 64k | $1/$5 por MTok | Extended | Feb 2025 |
Capability: Opus 4.8 = deepest reasoning + long agentic; Sonnet 4.6 = balanced; Haiku 4.5 = fast/cheap volume.

## 2. DeepSeek
| Modelo | Contexto | Max Output | Preço (entrada/saída) | Thinking Mode | Features |
| deepseek-v4-pro | 1M tokens | 384k | $0.435/$0.87 por MTok | Sim | Tool calls, JSON |
| deepseek-v4-flash | 1M tokens | 384k | $0.14/$0.28 por MTok | Sim (default) | Tool calls, JSON |
Capability: V4-Pro = max reasoning quality; V4-Flash = best cost/benefit. Both: Thinking Mode + Tool Calling + JSON output.

## 3. Kimi (Moonshot AI)
| Modelo | Contexto | Multimodal | Thinking | Agent Mode | API |
| kimi-k2.6 | 256k tokens | Texto + Imagem | Sim | Sim | OpenAI-compatible |
| kimi-k2.5 | 256k tokens | Texto + Imagem | Sim | Sim | OpenAI-compatible |
Capability: 256k context; multimodal (text+image); Thinking + Agent Mode; OpenAI-compatible API. (Note: kimi runs as a CLI code-executor in this workspace.)

## 4. Gemini (Google)
| Modelo | Preço (entrada/saída) | Thinking | Search Grounding | Batch API |
| Gemini 3.5 Flash | $1.50/$9.00 por MTok | Sim | Sim | 50% desconto |
| Gemini 3.1 Pro | $2.00/$12.00 por MTok | Sim | Sim | 50% desconto |
| Gemini 3.1 Flash-Lite | $0.25/$1.50 por MTok | Sim | Sim | 50% desconto |
Capability: Thinking tokens (in output price); Search Grounding (real-time web); Batch API 50% off. 3.5 Flash = smartest; 3.1 Flash-Lite = cheapest.

## 5. OpenAI
| Modelo | Contexto | Especialidade | Coding | Agentic |
| GPT-5.5 | ~200k | Geral | Avançado | Sim |
| GPT-5.4 mini | ~200k | Leve | Bom | Sim |
| GPT-5.4 nano | ~200k | Ultra-leve | Básico | Sim |
Capability: GPT-5.5 = top reasoning + coding; mini/nano = lighter/cheaper.

## 6. Cohere
| Modelo | Visão | RAG Nativo | Tool Calling | Reranking |
| Command A+ | Sim | Sim | Sim | Integrado |
| Command R | Não | Sim | Sim | Integrado |
Capability: Command A+ = vision + native RAG + reranking; Command R = lighter RAG.

## 7. Manus
| Aspecto | Descrição |
| Autonomia | Navegação de browser, cliques, interações |
| API | RESTful |
| Timeout | Até 5 minutos |
| Custo | Por tarefa |
| Integração | Múltiplas ferramentas e APIs |
Capability: real autonomy — browser navigation, clicks, form-fill, full workflows; RESTful task API; per-task cost; ~5-min timeout. Complement to LLMs, not a substitute.

## 8. Qwen (Alibaba)
| Modelo | Multimodal | Agent | Contexto | API |
| Qwen3.7 | Texto, imagem, vídeo | Sim | Não especificado | OpenAI-compatible |
| Qwen3.5-Plus | Texto, imagem, vídeo | Sim | Não especificado | OpenAI-compatible |
Capability: multimodal (text/image/video); Agent Mode; OpenAI-compatible.

## Matriz de Decisão Rápida (translate to English)
| Necessidade | Provedor | Modelo | Razão |
| Raciocínio máximo | Anthropic | Opus 4.8 | Adaptive Thinking |
| Custo-benefício | Anthropic | Sonnet 4.6 | Balanço ideal |
| Volume alto | Anthropic | Haiku 4.5 | Mais econômico |
| Raciocínio lógico | DeepSeek | V4-Pro | Thinking Mode |
| Custo otimizado | DeepSeek | V4-Flash | Muito barato |
| Contexto gigantesco | Kimi | K2.6 | 256k tokens |
| Visão + contexto | Kimi | K2.6 | Multimodal nativo |
| Processamento volume | Gemini | 3.1 Flash-Lite | Muito barato |
| Busca integrada | Gemini | 3.5 Flash | Search Grounding |
| RAG corporativo | Cohere | Command A+ | RAG nativo |
| Autonomia | Manus | API | Browser automation |
| Multimodal avançado | Qwen | 3.7 | Vídeo + imagem |

## Source citation URLs (keep these)
- Anthropic: https://platform.claude.com/docs/en/about-claude/models/overview
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing , https://api-docs.deepseek.com/guides/thinking_mode
- Kimi: https://platform.kimi.ai/docs/models , https://platform.kimi.ai/docs/api
- Gemini: https://ai.google.dev/gemini-api/docs/models , https://ai.google.dev/gemini-api/docs/pricing
- OpenAI: https://platform.openai.com/docs/models
- Cohere: https://docs.cohere.com/docs/models , https://docs.cohere.com/docs/rag
- Qwen: https://dashscope.aliyuncs.com/docs
- Manus: https://api.manus.im/docs
```

## Validation (before returning)
1. The four in-scope API providers (DeepSeek, Gemini, OpenAI, Manus) — plus Claude/Kimi/Qwen/Cohere for context — each have their model table present and in ENGLISH.
2. The verbatim reference-data header is at the top; the OpenAI codex-CLI note is present.

## Return — provide EXACTLY these five fields as your final message:
- **status:** DONE | DONE_WITH_NOTES | BLOCKED | DOUBT_ESCALATED | NEEDS_CONTEXT
- **landed:** `orchestration/docs/routing-matrix-reference.md` created (NO commit — conductor commits)
- **validation:** what you checked (sections present, English, header) + result; SKIPPED_COUNT
- **concerns:** anything the conductor should weigh
- **open_questions:** unresolved questions
