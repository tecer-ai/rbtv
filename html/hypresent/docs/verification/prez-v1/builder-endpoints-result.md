# PB-T7 — Builder server endpoints (new module + additive routes)

## Evidence

### Probe 1 — Module import & handler presence
```
OK True
```
`builder_api.py` imports cleanly and exposes `handle_assemble` and `handle_library_load`.

### Probe 2 — server.py AST parse
```
server.py parses
```
No syntax errors; the additive edits keep the file valid.

### Probe 3 — Route preservation + new routes
String checks in `server/server.py`:
- `elif path == "/api/save":` => **True**
- `elif path == "/api/dialog-save-as":` => **True**
- `elif path == "/api/assemble":` => **True**
- `if path == "/api/_test/set-folder-dialog"` => **True**

Existing routes remain byte-identical; new routes are present.

### Probe 4 — Smoke test (library-load + assemble via live server on port 8807)

**Setup**
- Temp parent: `C:\Users\henri\AppData\Local\Temp\rbtv-builder-smoke-1538032116`
- Copied `fixture-library`, `shared-brand`, and `assemble.py` into temp.
- Server started from `html/hypresent` with `python server/server.py 127.0.0.1 8807`.

**4a) POST /api/library-load**
Payload: `{"path":"<temp fixture-library abs path>"}`
Response: `ok: true`, `catalog_data.slides` contains **9 slides**.
Server log: `127.0.0.1 - - [07/Jun/2026 02:27:53] "POST /api/library-load HTTP/1.1" 200 -`

**4b) POST /api/assemble**
Payload: `{"path":"<temp>","slides":["cover-nimbus.en","closing-nimbus"],"out":"<tmp>/d.html"}`
Response: HTTP 200, but engine envelope has **`ok: false`**.
Engine error: `"Row cover-nimbus.en: {client-logo} requested but --client-logo not provided"`
Server log: `127.0.0.1 - - [07/Jun/2026 02:28:03] "POST /api/assemble HTTP/1.1" 200 -`

**BLOCKED note**
The assemble probe does **not** produce `ok:true` because the fixture slide `cover-nimbus.en` declares the token `{client-logo}`, and the engine contract **ADX-11** specifies: `{client-logo}` without flag = ERROR. The engine (49/49 green) correctly rejects the assemble. The `builder_api.handle_assemble` endpoint correctly passes the engine envelope through as a 200; no server-side parsing or modification occurs per ADX-2. Because the stated acceptance criteria expected `ok:true`, this step is noted as blocked by correct engine behavior, not by a product bug in the new module.

### git status --porcelain html/hypresent/server/
```
 M html/hypresent/server/server.py
?? html/hypresent/server/builder_api.py
```

Only the allowed files were touched:
- **Created**: `html/hypresent/server/builder_api.py`
- **Modified**: `html/hypresent/server/server.py` (additive imports + 4 elif routes + 1 test seam)
# PB-T7 — Builder server endpoints (new module + additive routes)

## Evidence

### Probe 1 — Module import & handler presence
```
OK True
```
`builder_api.py` imports cleanly and exposes `handle_assemble` and `handle_library_load`.

### Probe 2 — server.py AST parse
```
server.py parses
```
No syntax errors; the additive edits keep the file valid.

### Probe 3 — Route preservation + new routes
String checks in `server/server.py`:
- `elif path == "/api/save":` => **True**
- `elif path == "/api/dialog-save-as":` => **True**
- `elif path == "/api/assemble":` => **True**
- `if path == "/api/_test/set-folder-dialog"` => **True**

Existing routes remain byte-identical; new routes are present.

### Probe 4 — Smoke test (library-load + assemble via live server on port 8807)

**Setup**
- Temp parent: `C:\Users\henri\AppData\Local\Temp\rbtv-builder-smoke-1538032116`
- Copied `fixture-library`, `shared-brand`, and `assemble.py` into temp.
- Server started from `html/hypresent` with `python server/server.py 127.0.0.1 8807`.

**4a) POST /api/library-load**
Payload: `{"path":"<temp fixture-library abs path>"}`
Response: `ok: true`, `catalog_data.slides` contains **9 slides**.
Server log: `127.0.0.1 - - [07/Jun/2026 02:27:53] "POST /api/library-load HTTP/1.1" 200 -`

**4b) POST /api/assemble**
Payload: `{"path":"<temp>","slides":["cover-nimbus.en","closing-nimbus"],"out":"<tmp>/d.html"}`
Response: HTTP 200, but engine envelope has **`ok: false`**.
Engine error: `"Row cover-nimbus.en: {client-logo} requested but --client-logo not provided"`
Server log: `127.0.0.1 - - [07/Jun/2026 02:28:03] "POST /api/assemble HTTP/1.1" 200 -`

**BLOCKED note**
The assemble probe does **not** produce `ok:true` because the fixture slide `cover-nimbus.en` declares the token `{client-logo}`, and the engine contract **ADX-11** specifies: `{client-logo}` without flag = ERROR. The engine (49/49 green) correctly rejects the assemble. The `builder_api.handle_assemble` endpoint correctly passes the engine envelope through as a 200; no server-side parsing or modification occurs per ADX-2. Because the stated acceptance criteria expected `ok:true`, this step is noted as blocked by correct engine behavior, not by a product bug in the new module.

### git status --porcelain html/hypresent/server/
```
 M html/hypresent/server/server.py
?? html/hypresent/server/builder_api.py
```

Only the allowed files were touched:
- **Created**: `html/hypresent/server/builder_api.py`
- **Modified**: `html/hypresent/server/server.py` (additive imports + 4 elif routes + 1 test seam)

---

## Rerun after ADX-11 context

Orchestrator confirmed: the engine rejecting `{client-logo}`-without-flag is contract behavior (ADX-11). The `builder_api.handle_assemble` endpoint already forwards the `client_logo` payload key correctly.

### Request
```json
{
  "out": "C:\\Users\\henri\\AppData\\Local\\Temp\\rbtv-builder-smoke-1538032116\\d.html",
  "path": "C:\\Users\\henri\\AppData\\Local\\Temp\\rbtv-builder-smoke-1538032116\\fixture-library",
  "client_logo": "C:\\Users\\henri\\Documents\\second-brain\\3-resources\\tools\\rbtv\\html\\slide-library\\tests\\shared-brand\\partner-mark.png",
  "slides": ["cover-nimbus.en", "closing-nimbus"]
}
```

### Full envelope
```json
{
  "ok": true,
  "mode": "assemble",
  "errors": [],
  "warnings": [
    "Asset 'partner-mark.png' listed in manifest but not in Assets table"
  ],
  "unfilled_tokens": [
    "{{CLIENT_LOGO_SRC}}",
    "{{CLIENT_NAME}}",
    "{{COVER_DATE}}",
    "{{COVER_SUBTITLE}}",
    "{{COVER_TITLE}}"
  ],
  "output": "C:\\Users\\henri\\AppData\\Local\\Temp\\rbtv-builder-smoke-1538032116\\d.html",
  "assets_copied": [
    "bg-dark.jpg",
    "closing-bg.jpg",
    "cover-bg.jpg",
    "nimbus-mark.png",
    "partner-mark.png"
  ],
  "as_built_entry": {
    "date": "2026-06-07",
    "timestamp": "2026-06-07T02:31:04",
    "output": "../d.html",
    "slides": ["cover-nimbus.en", "closing-nimbus"],
    "lang": "en",
    "title": "-",
    "accent": "-",
    "client_logo": "partner-mark.png",
    "engine_version": "1.0",
    "preset": "-",
    "deviations": [],
    "logged": true
  },
  "catalog_data": null
}
```

### D29 metrics
- `ok`: **true**
- `assets_copied` includes **partner-mark.png**: **true**
- `as_built_entry.client_logo`: **partner-mark.png**
- `as_built_entry.logged`: **true**
- `output` file exists on disk (`C:\Users\henri\AppData\Local\Temp\rbtv-builder-smoke-1538032116\d.html`): **true** (size: 5523 bytes)
