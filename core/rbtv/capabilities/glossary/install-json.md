# `install.json`

`install.json` is the installation root’s record at `.rbtv/config/install.json`. It holds the selected files and packs, receiving harnesses and rbtv’s record of generated files and shared-file ownership. rbtv uses it to distinguish what it may update or remove from the author’s own files.

Use the [schema](../templates/install-json.schema.json) for its fields and [rbtv CLI](rbtv-cli.md) for setup and changes. The first configuration or add creates the record. Record format 9 reads the selected files under `files` or the older `units`, and each component's installed files under `selected` or the older nested `units`; rbtv rewrites an older name as the current one the next time it writes the record. An agent folder uses [agent.json](agent-json.md) instead; the root has no stored model or effort for its interactive sessions.

Change selections through rbtv or edit the selection fields and apply the refresh specified by rbtv CLI. Editing the record alone does not change the generated files. Applying a selection also removes generated files no longer selected. Leave rbtv’s generated-file and ownership records to the software; do not maintain a second installation list.

Keep this record on its machine and exclude it from git. Keep absolute paths and timestamps out of it. Each machine maintains its own installation selections, while [path-owners.json](path-owners-json.md) records commands shared by installations on that machine.

`transcription_model` and `generation_model` independently select the installation's audio defaults as `connector/model`, such as `onnx-asr/nemo-parakeet-tdt-0.6b-v3` and `elevenlabs/eleven_flash_v2_5`. An agent's nonblank field of the same name overrides that operation only. Missing, null or blank agent fields inherit the current installation value. Ignite reads these choices at every audio operation; editing them requires no refresh or service restart. With no selection at either level, an existing Ignite installation keeps using its configured `tools.audio` command. Keep model paths and executor settings in the connector's own configuration folder.

After changing a selection, check the installed listing and generated files. Run `rbtv doctor` to check them against the saved record; merely accepting an edit does not prove the folder matches it.
