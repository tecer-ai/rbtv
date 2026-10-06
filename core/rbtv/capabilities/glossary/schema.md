# Schema

A schema, in rbtv, is the JSON Schema file a CLI loads when it checks the fields of a record or of frontmatter. Outside rbtv, a validator of the draft that the file names applies every keyword of that draft. Here the check applies only the keywords that `errors` reads. A schema file that no call of `load` reads checks nothing.

A schema is for a constraint a CLI can refuse the same way on every run, in place of a sentence that an author of a record may skip. An author wants one when a CLI reads a record of fixed fields and a wrong field must be refused before that CLI acts on the record. Write a schema so that the call that loads it refuses a record that breaks the constraint. A matching record is one that call can read by the keys it already uses.

## How it fails

The CLI can accept a schema, and the schema can still fail, because `load` reads the file as JSON and `errors` applies only the keywords it implements.

- A constraint sits only in a property's `description`, or it uses a keyword that `errors` does not read, such as `format`, `$ref`, `if`, `then`, `allOf` or `patternProperties`. A record that breaks the constraint is not refused, and the CLI reads the field.
- The file's stem is not the string a call passes to `load`, or the file sits outside the directory that `SCHEMA_DIR` names. No call applies the file. A record that breaks it is not refused.
- `additionalProperties` is absent. A field that the schema does not name stays in the value that the call submitted. The CLI then reads the keys that its code names, so the extra field stays and is not used.
- A required property is added to `install-json.schema.json`, `path-owners-json.schema.json` or `ignite-config.schema.json`, and the writer of that record is left as it is. Those writers do not call `load` on that stem. The old shape is still written.
- A required property is added to `agent-json` outside the keys that `agents.py` submits. That call builds an object without the new key, so every installed agent is reported missing it, including a file that has the key.
- The property name changes in the schema, and the line that reads the key does not. The CLI still reads the old name.
- A `pattern` has no `^` and no `$`. The check searches for a match inside the value. A longer value that contains the pattern is not refused.
- A property contains a secret. The record is a file that the CLI reads, and a copy of the record may leave the machine.

## What it is composed of

The author writes one file, `<name>.schema.json`. `<name>` is the string a call passes to `load`, not the title of a glossary entry and not the `title` in the file. The file sits in the directory that `SCHEMA_DIR` names in `core/rbtv/capabilities/tools/rbtv/lib/schema.py`. That directory is `core/rbtv/capabilities/templates/`. A file in another directory is not loaded by this `load`.

`load` reads `<name>.schema.json` and returns the object. `errors` compares a value with that object. It reads `type`, `required`, `properties`, `additionalProperties`, `items`, `enum`, `const`, `pattern`, `minLength`, `minimum`, `minItems`, `uniqueItems`, `oneOf` and `not`. It does not read `title`, `description`, `format`, `$schema`, or any other keyword. A keyword that it does not read never refuses a value. `$schema` in the files that exist today names draft 2020-12. That line does not make `errors` a validator of that draft.

The file may carry `$schema`, `title` and a top-level `description`. The check does not read them. The top-level `description` says which call loads the file, for the person who reads the file. Each property has a `description` that says what the field is. The check does not read that line. The entry of the record links this file and does not repeat the fields, so that line is what the author of the record reads.

These calls load a stem. The page "rbtv CLI"¹ says which source the scan checks against each stem, and what a pass of that source shows. This page does not say how to run the rbtv CLI.

- The scan in `discovery.py` calls `load` with `module-json`, `component-json`, `pack`, `skill`, `rule`, `command`, `agent`, `agent-json`, `hook`, `mcp-server`, `folder-instructions` and `tool-json`. It submits the whole frontmatter or the whole JSON.
- `agents.py` calls `load` with `agent` for the frontmatter of an installed agent. It calls `load` with `agent-json` and submits only `name`, `description`, `harness`, `model`, `effort`, `files` and `packs`.
- `selftest/test_subagents.py` calls `load` with `install-json`. The writer in `state.py` does not. It checks the record in `_validate_state`.
- `shared_links.py` does not call `load` with `path-owners-json`. It checks that record in `_read_owners`. `core/ignite/capabilities/tools/ignite/config.js` does not read `ignite-config.schema.json`. It checks the config in `validate`.

## How to build it

1. **The record that the check must refuse, then the purpose.** Before a line of the file, name three things. The failure is a record that the next run keeps. Its field breaks the constraint that this file was meant to apply. The cause, for a schema, is a constraint that the check does not apply: no call loads this file, `errors` does not read the keyword, or the call does not submit the field. Find that cause in the call list above, and in the keywords that `errors` reads. The situation is the next record of that kind, as the CLI writes it or reads it today. Then write the purpose from the failure: the call refuses a record that breaks the constraint. A record that matches is one that call can read by the keys it already uses.

   Weak: "A reader of the skill schema sees that `name` is a string."

   Strong: "The scan calls `load` with `skill` and refuses a frontmatter whose `name` fails `^[a-z0-9][a-z0-9-]*$`. A frontmatter that matches is one the scan reads by `name` and `description`."

   The weak line names a reader and no keyword that `errors` reads. A frontmatter with a bad `name` is not refused by anything the author added.

2. **Name the file as the string the call passes.** Put `<name>.schema.json` in the directory that `SCHEMA_DIR` names. `<name>` is that string. A glossary title, or the `title` inside the file, is not the string. A file outside that directory is not this check. `load` reads the path. A missing file is not turned into a schema error.

3. **Write one property for each field that the call reads.** The key is the key in the CLI, spelled the same way. Mark `required` only a field that the CLI cannot proceed without. A field that the CLI writes is still a property when a call submits it, so a later read can check it. Do not add a property that no call reads. The page "Keep it stupidly simple"² refuses a field that a stated need does not require. A property that no call reads is that field: the author of the record still has to decide whether to write it, the check applies the constraint when the call submits the whole record, and the CLI then does nothing with the value.

   Weak: "Add `color`, not required, so a later task can name a color."

   Strong: "Add no `color`. No call reads `color`."

   The weak line adds a property for a need that nobody has stated. The author of the record has to decide whether to write it, and no call reads the value.

4. **Refuse an unnamed field only by setting `additionalProperties`.** When the keyword is absent, the check keeps a field that the schema does not name. JSON Schema does the same when the keyword is absent, so a reader who knows that draft still has to set it here. Set it to `false` when a call that submits the whole value must refuse that field. Set it to a schema when every unnamed field must match that schema. Leave it absent only when an unnamed field must stay, and name the call that needs that. When the call submits only some keys, a field that it left out is not seen, so `false` does not refuse that field on that call.

   Weak: "Leave `additionalProperties` out. The `properties` list is the fields."

   Strong: "Set `additionalProperties` to `false`, so a call that submits the whole value refuses a field that this schema does not name."

   The weak line leaves the default. The check keeps the extra field. The CLI reads the keys that its code names, so the extra field stays and is not used.

5. **Put each constraint in a keyword that `errors` reads.** Use one of the keywords named above. A constraint in `description`, `title`, `format` or `$schema` is not applied. A keyword that the function does not read, such as `$ref`, `if`, `then` or `patternProperties`, is not applied. Anchor a `pattern` that must match the whole value, with `^` and `$`, because the check searches inside the value. Use `oneOf` when the value must match exactly one shape. A value that matches two shapes fails, and so does a value that matches none. Use `not` when a shape must be absent. Write the property's `description` as what the field is, in one line, because the entry of the record does not repeat the fields and the check does not read the line. When the record's author needs a minimum, write the number in that line.

   Weak: "The description says the value must be a slug of at most 64 characters."

   Strong: "The `pattern` is `^[a-z0-9][a-z0-9-]{0,63}$`. The description says the value is a slug of at most 64 characters."

   The weak line puts the constraint where the check does not read it. A longer value is not refused.

6. **Change the call in the same change as the field.** A new property does not make the CLI read a new name. In the same change, change the schema, the line that reads the key, and any sentence in the entry of the record that states who writes the field or when the field is present. Do not add a field list to that entry. The schema is the home of the fields. The line that reads a key is the home of what the CLI reads. The page "Single source of truth"³ is that rule. The page "Writing a glossary entry"⁴ is the rule for the entry of a record: link this file, and do not list the fields. When no call loads this file, change the writer so that it loads the file, in the same change. Otherwise the edit refuses nothing.

   For `agent-json`, the call in `agents.py` submits only the seven keys named above. A new required property outside that list is reported missing on every installed agent, because the submitted object does not have the key. Add the key to that submission in the same change, or do not mark it required.

   Weak: "Add `voice` to `required` in `agent-json`."

   Strong: "Add `voice` to `required` in `agent-json`, and add `voice` to the keys that `agents.py` submits, in the same change."

   The weak line changes the schema only. The submitted object has no `voice`, so every installed agent is reported missing that key, including a file that has it.

7. **A property that carries a secret names the variable that has it, never the value.** The record is a file that the CLI reads, and a copy of it may leave the machine. Constrain such a property to the form of a variable name, so that a value that does not have that form fails the check; a secret that happens to have that form passes, so the check is not a detector of secrets.

   Weak: "The property `token` is a string, the token."

   Strong: "The property `tokenEnv` is a string, the name of the variable. The value stays in the environment."

   The weak line puts the secret in the record. A copy of the record carries it.

When you edit a field, the schema file is the copy you change for the fields. The line that reads the key is the copy you change for what the CLI reads. An edit of only the schema reaches a record on the next call that loads that stem and submits that field. It does not reach a writer that does not call `load`.

When you convert an outside JSON Schema, move each constraint into a keyword that `errors` reads. Do not leave it in `$ref`, `format`, `if` or `then`. A draft validator would follow those. This check does not.

When you review a schema, open the call that passes its stem. A property that the call does not submit is not checked. A keyword that `errors` does not read never refuses. An unnamed field is refused only where `additionalProperties` is `false`, or is a schema that the field fails, and the call submits the whole value.

Checks:

- The file stem equals the string a call passes to `load`, and the file sits in the directory that `SCHEMA_DIR` names. Each constraint is a keyword that `errors` reads. `additionalProperties` is `false` where an unnamed field must be refused on a call that submits the whole value. Each property's `description` says what the field is. No property contains a secret. The entry of the record links the file and has no field list.
- An empty list from `errors` shows that the submitted value matched the keywords that the call read. It does not show that the CLI uses the field after the match. It does not show that a keyword `errors` ignores was applied. It does not show that the entry of the record agrees. A file that no call loads has no such pass. What a pass of a recognized source shows is the page "rbtv CLI"¹.
- Take a stem that a call loads. Change one keyword, and submit a value that breaks it. The list from `errors` is not empty. Then add a required property to `ignite-config.schema.json` only, and read `validate` in `config.js`. That function still does not read the file, so the old config is still written.

## Template

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "<a label for a person who reads the file; the check does not read it>",
  "description": "<which call loads this file; the check does not read it>",
  "type": "object",
  "required": ["<a field the CLI cannot proceed without>"],
  "additionalProperties": <false when an unnamed field must be refused on a call that submits the whole value; a schema when every unnamed field must match it; omit the keyword when an unnamed field must stay>,
  "properties": {
    "<the key the CLI reads>": {
      "type": "<string, integer, number, boolean, object or array>",
      "description": "<what the field is, including a minimum the report will not name>"
    }
  }
}
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | a stem is one the scan loads, and a pass of a source is being read | take which source the scan checks against that stem, and what that pass shows |
| 2 | Keep it stupidly simple | [Keep it stupidly simple](../principles/keep-it-stupidly-simple.md) | when | deciding whether to add a property | refuse a field that a stated need does not require |
| 3 | Single source of truth | [Single source of truth](../principles/single-source-of-truth.md) | when | a field change would be written in a second file | change the file that changes with the fact, and link the others |
| 4 | Writing a glossary entry | [Writing a glossary entry](../writing-a-glossary-entry.md) | when | the entry of the record is edited in the same change | link the schema from that entry, and do not list the fields |
