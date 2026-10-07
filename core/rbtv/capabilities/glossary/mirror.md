# `mirror/`

`.rbtv/mirror/` holds component source local to one installation. rbtv scans it alongside repository source and installs its selected files through the same process.

Use [Choosing where to build](../methods/choosing-where-to-build.md) to settle whether the source belongs here. Write a local component with the [Component](component.md) layout. For an imported or shareable skill that keeps its own supporting files, follow [Self-contained skill](self-contained-skill.md) instead.

Follow Choosing where to build’s identity rule for additions and whole-component replacements. For a replacement, include the files its users still need and make every omission intentional. Scanner acceptance validates recognized records and files, not whether the replacement preserves users’ work; [rbtv CLI](rbtv-cli.md) owns those checks.

Edit the mirror source and apply the required refresh. While the replacement is active, check the selected source and installed files: an omitted file must not reappear merely because the repository component contains it. To stop replacing that component, remove its mirror component and refresh; check that the repository source is selected again.
