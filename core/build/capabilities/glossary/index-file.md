# Index file

The [folder artifact](folder-artifact.md) named `<folder>.md` that lists a folder's items and states when to open each. It holds the list, never the items' content. A folder has one when its items are needed at different moments. Module, component, and tool folders have none: their JSON record, [`<module>.json`](module-json.md), [`<component>.json`](component-json.md), or [`<tool>.json`](tool-json.md), describes them. In a component's unit folders, such as `skills/` or `rules/`, the installer reads `<folder>.md` as that folder's index file, never as a unit.
