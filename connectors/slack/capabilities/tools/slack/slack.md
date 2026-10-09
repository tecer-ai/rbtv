# Slack

`slack` reads and searches messages, transfers files, sends messages, manages reactions and edits canvases. Run `slack --help` and the selected verb's help for arguments and outcomes.

Install with `rbtv add --component connectors/slack`. The installer clones the branch in `slack.json` when missing and sets up its Python environment. Repeating installation does not pull updates; `rbtv update repositories` explicitly updates selected external repositories and refuses checkouts with local changes.

The wrapper runs this component's `repository/stools.py`. `SLACK_TOOLS_ROOT` overrides the checkout; `SLACK_TOOLS_CONFIG` overrides `.rbtv/config/slack/config.yaml` in the installation. Run from inside the installation so account selection and grants resolve there. Credentials follow the external repository's configuration contract.

## Messages and preview

Write messages in standard Markdown. Send and upload dry runs show the complete message fields used for delivery; this is an outgoing-content preview, not a rendering of Slack's interface. Each message is limited to 12,000 characters. Attach longer documents instead of truncating them.

Text uses Slack's native `markdown_text` field. Upload captions use a `markdown` block, without `initial_comment`, which would override it. Broadcast uploads post the caption once through the text path. The tool does not guess a second input format or silently retry a failed write in another format. Slack determines visual rendering; headings share one size and Markdown images become links. Maintainers should check [chat messages](https://docs.slack.dev/reference/methods/chat.postMessage/), [Markdown blocks](https://docs.slack.dev/reference/block-kit/blocks/markdown-block/) and [upload completion](https://docs.slack.dev/reference/methods/files.completeUploadExternal/) before changing these fields.

Reply in the thread the request belongs to. File conversion is handled by its provider, such as `elevenlabs`; Slack transfers the resulting local file. Ignite replies go through `replies[].text` and `replies[].files`, not a second manual post; Ignite owns that delivery contract.

## Write identity

An account label does not prove the Slack identity. Use the account and recipient authorized by the request. Writes on accounts configured with `writes: false` additionally require a matching active grant in `.rbtv/config/slack/write-grants.yaml`. Preserve existing grants and record only the approved account, verbs and working-folder scope. The command's send help links the grant format.

The matcher checks account, verb, active status and working-folder scope. It does not enforce a thread, message count, expiry or consent authorship. A grant is not consent, `--yes` only skips interactive recipient confirmation, and a dry run does not establish permission or grant coverage. Missing account metadata fails closed for writes. Reads are not subject to write grants. Help requires no grants; no Slack operation occurs while showing help.
