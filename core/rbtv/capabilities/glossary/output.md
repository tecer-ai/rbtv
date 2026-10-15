# `output/`

`output/` holds what a component produces for people to read and rule on: a backlog of entries awaiting the owner's ruling, a study note, a report. It is the third kind of data a component keeps, beside [config/](config.md), what the user chose or supplied, and [runtime/](runtime.md), what the component needs in order to run. Output is a record for a reader; runtime is operational data no reader is owed.

An installation's output is `.rbtv/output/<component>/`, one folder named exactly as the component, as config and runtime name theirs. An agent's output is `output/<component>/` inside the agent folder, for what a component produced about that agent alone. [Folder structure](../methods/folder-structure.md) shows both trees; do not copy them here.

The method that produces the record names its file inside that folder and creates the folder on first use; rbtv does not prepare it. A method that has nothing for a reader writes nothing here: its state, caches, locks and logs are runtime.

Output is tracked in git, at both levels, so a record reaches the owner's other machines and survives a reinstall. A method whose output is private writes its own `.gitignore` inside its folder before its first file, as the work-history collection does. The installer's ignore block never covers `output/`.

An installation's instruction file may name another place for one method's output, as it names a project's backlog; the method follows that place and writes to `output/` only when none is named.

Exercise the operation that writes the record and a read of it from a fresh session. Check that both use `output/<component>/`, that a first write in an installation without the folder creates it, and that the file is tracked.
