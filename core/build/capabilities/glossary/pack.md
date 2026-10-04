# Pack

A named list of units that a component declares in `packs/<name>.json`, a readable data file. Its fields are defined by its [schema](../templates/pack.schema.json): a description, and the `units` it lists as full ids `<module>/<component>#<unit>`. The pack's name is the file's name, and it is unique across the catalog.

A root or an agent turns a pack on or off. Its `packs` field in the record of [`agent.json`](agent-json.md) or [`install.json`](install-json.md) lists the packs that are on. A pack is named only through `--pack NAME` on the [`rbtv` command](rbtv-command.md). When a pack is on, its units are installed; `add`, `update` and `remove` treat them like any other unit. A unit is generated once however many ways it was chosen. Turning a pack off removes its units, except those listed in `units` or in another pack that is on.

The Ignite pack is the pack that the `ignite` component declares. It holds the standard units of an [Ignite agent](agent.md#ignite-agent). `ignite connect` turns it on, and `ignite disconnect` turns it off.
