# Prompting Assistance Knowledge

This folder contains indexes and references for the prompting-assistance workflow.

## Structure

| File | Purpose |
|------|---------|
| `knowledge-index.csv` | Index of all knowledge types with paths |
| `ai_models/` | AI model-specific prompting guides |
| `prompting_techniques/` | Reusable prompting technique guides |
| `platform_knowledge/` | Platform interface guidance (Claude Projects, ChatGPT Projects, etc.) |

## Source Location

The master knowledge files are maintained in:
- `robotville/system/ai_pro/prompting/ai_models/`
- `robotville/system/ai_pro/prompting/prompting_techniques/`
- `robotville/system/ai_pro/platform_knowledge/`

## Usage

The workflow uses `knowledge-index.csv` to:
1. Present available knowledge to user
2. Load relevant files based on user's prompting needs
3. Recommend techniques based on problem type

## Alternative: Direct Reference

If you prefer NOT to copy files, the workflow can reference the robotville paths directly. The `knowledge-index.csv` contains the source paths for this purpose.
