# rbtv installer

The program that reads each [`<module>.json`](module-json.md) and [`<component>.json`](component-json.md), identifies what a component offers from the folders its files sit in, checks each file's frontmatter against its [schema](schema.md), writes the selected harness's files, and makes declared tools available on `PATH`. It also creates and maintains the target folder's `.rbtv/` structure and the user's [`~/.rbtv/`](rbtv-home-folder.md). It marks every file it generates with `rbtv-managed`, so it recognises its own files.
