# Folder artifact

A standard file a folder an agent maintains can hold, with one fixed purpose, living in that folder's visible `_artifacts/` under a plain name, such as the [board](board.md) or the [index file](index-file.md). `_artifacts/` does not replace rbtv's `capabilities/` folders. Those stay where they are.

rbtv's JSON records stay beside their folder, not in `_artifacts/`: [`<module>.json`](module-json.md), [`<component>.json`](component-json.md), [`<tool>.json`](tool-json.md), and an agent folder's [`launch.json`](launch-json.md) and [`settings.json`](settings-json.md). They are records programs read, not navigation artifacts. A module, component, or tool folder has its JSON record and no index file.

A wiki keeps its own index names, so links by file name keep working. The [task file](task-file.md) is the one plain-name exception, because the task tool matches the `-tasks.md` ending.

Folder artifacts give a folder a structure agents can navigate. An agent opens one when a pointer or the folder leads it there. They are [cognitive units](cognitive-unit.md). A folder artifact is never exposed as a [skill](skill.md), a [rule](rule.md), a [command](command.md), or an [agent](agent.md).
