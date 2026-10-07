# Schema

A schema is the JSON Schema file an rbtv program loads to validate a record or frontmatter. Use it for a constraint the program must enforce before acting on fixed fields. A schema enforces nothing unless the actual caller loads it, submits the relevant value and supports the keywords used.

## Validator and callers

Write `<name>.schema.json` in `core/rbtv/capabilities/templates/`, the directory named by `SCHEMA_DIR` in `tools/rbtv/lib/schema.py`. The stem must be exactly the string passed to `load`; neither the glossary title nor the schema's `title` controls lookup. A missing file is not converted into a validation error.

`load` reads JSON. `errors` applies only these keywords: `type`, `required`, `properties`, `additionalProperties`, `items`, `enum`, `const`, `pattern`, `minLength`, `minimum`, `minItems`, `uniqueItems`, `oneOf` and `not`. It ignores other keywords, including `format`, `$ref`, `if`, `then`, `allOf` and `patternProperties`. Declaring draft 2020-12 in `$schema` does not turn it into a complete validator for that draft.

| Caller | What reaches validation |
|---|---|
| `discovery.py` | Whole frontmatter or JSON for `module-json`, `component-json`, `pack`, `skill`, `rule`, `command`, `prompt`, `agent-json`, `hook`, `mcp-server`, `folder-instructions` and `tool-json`. |
| `agents.py` | Prompt frontmatter through `prompt`; only `name`, `description`, `harness`, `model`, `effort`, `files` and `packs` through `agent-json`. |
| `selftest/test_subagents.py` | Loads `install-json` in tests. The production writer in `state.py` uses `_validate_state`, not that schema. |
| `shared_links.py` | Uses `_read_owners`; does not load `path-owners-json`. |
| Ignite's `config.js` | Uses `validate`; does not load `ignite-config.schema.json`. |

Use [rbtv CLI](rbtv-cli.md) for source-to-schema mapping and commands. This page owns validator constraints, not the command interface.

## Write an enforced constraint

First identify the bad value to reject and the actual call that receives it. Add only fields the program needs and reads, using its exact key names. Require a field only when the program cannot proceed without it. Update the reader, writer and submitted keys with the schema; adding a required agent field outside the seven submitted keys makes every installed agent fail, even when its file contains the field.

Set `additionalProperties: false` when unknown fields must be rejected. Use a schema value when arbitrary extra keys must satisfy a constraint. Omit it only when extras are deliberately allowed, naming the caller that needs them. A caller that submits selected keys cannot validate extras it left out.

Put constraints in supported keywords. Anchor whole-value patterns with `^` and `$`; matching otherwise searches within the value. `oneOf` requires exactly one matching alternative, and `not` rejects its matching shape. A prose description cannot enforce a constraint or an ignored keyword.

Give every property a one-line description explaining the field, including numeric limits its author needs. A top-level description names the loading call. `$schema`, `title` and descriptions help authors but are not validation behavior. The record's glossary entry links the schema instead of repeating its field list.

Credential fields name environment variables, never secret values. Constrain the variable-name form, while recognizing that a secret resembling a variable name can still pass. Validation is not secret detection.

## Change and test together

When changing a field, update the schema, consuming code and affected authoring instructions in the same change. If the intended writer does not load the schema, wire validation into that writer as part of implementing the constraint; merely changing the schema does not enforce it. Follow the applicable coding instructions before changing code.

When converting another schema, translate constraints into supported keywords or implement the missing validator behavior explicitly. Do not leave an unsupported keyword as if it worked.

Exercise the actual loading call with a valid value and a value that breaks the changed constraint. Confirm rejection at that boundary and verify that the program uses the accepted field afterward. For callers that do not load a schema, test their real validator rather than claiming schema coverage. An empty error list proves only that the submitted value passed the implemented keywords; it does not prove full draft compliance or agreement with the prose entry.

## Template

Use the actual stem and caller. The placeholder for `additionalProperties` is filled according to the extra-field policy above.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "<human-readable label>",
  "description": "<call that loads this schema>",
  "type": "object",
  "required": ["<key required by the program>"],
  "additionalProperties": <false or a schema; omit when extras are allowed>,
  "properties": {
    "<key the program reads>": {
      "type": "<supported JSON type>",
      "description": "<meaning and limits for the author>"
    }
  }
}
```
