# `install.json`

The install record: the file in [`.rbtv/config/`](config.md) where the [installer](rbtv-installer.md) records what it installed in a target folder, for which harnesses, and which files each installed component wrote. Every target folder has one, including each installed [agent](agent.md#installed-agent)'s folder, where it also lists the units the agent file selected, so an update removes only those the file drops and leaves units installed by other means, such as Ignite's. Programs read it; the installer reads it to update or remove what it installed.
