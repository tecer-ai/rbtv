# Google

`google` provides Google Workspace operations through this component's external repository. Run `google --help`, then the service and verb's help for the interface.

Install with `rbtv add --component connectors/google`. Installation clones the branch declared in `google.json` when missing and installs its Python requirements. Repeating installation repairs setup without pulling new code. `rbtv update repositories` explicitly updates selected external repositories; a checkout with local changes must be resolved before it can update.

The wrapper uses `repository/gtools.py` inside this component. `GOOGLE_TOOLS_ROOT` overrides the checkout. From an installation, configuration is `.rbtv/config/google/config.yaml`; `GOOGLE_TOOLS_CONFIG` overrides that path. Credentials remain relative to the external repository's configuration contract. Keep credential values out of source and output.

Select the account explicitly; discover configured accounts with `google accounts`. Use the account and recipient, calendar event or file established by the owner's request. Ask only when that context is uncertain. Inspect the command's actual result before reporting a draft, send, event change or file move as complete. A dry run proves only a preview, and is available only on the verbs that advertise it.
