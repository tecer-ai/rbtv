# PB-T6 — Builder page shell + nav (zero regression to the editor)

## Verification Results

### Probe 1: JS syntax check
```
Command: node --check html/hypresent/app/js/builder/builder-main.js
Exit code: 0
Output: (valid JS, no output)
Result: PASS
```

### Probe 2: Server 200 checks
```
Server started: python html/hypresent/server/server.py 127.0.0.1 8801
GET http://127.0.0.1:8801/app/builder.html → 200
GET http://127.0.0.1:8801/app/ → 200
Server stopped after probes.
Result: PASS
```

### Probe 3: Editor boot regression (index.html intact)
```
String check: id="open-btn"            → True
String check: class="shell-toolbar"    → True
String check: class="doc-frame"        → True
String check: <script type="module" src="/app/js/main.js"></script> → True
Result: PASS
```

### Probe 4: Nav link present in index.html
```
String check: <a href="/app/builder.html" class="app-nav-link" id="nav-builder">Builder</a> → True
Result: PASS
```

## git status --porcelain html/hypresent/app/
```
 M html/hypresent/app/index.html
?? html/hypresent/app/builder.html
?? html/hypresent/app/css/builder.css
?? html/hypresent/app/js/builder/
```

## D29 Metrics
- WALL_MS: 42000
- EXIT: 0
- SKIPPED_LINES_COUNT: 0

## BLOCKED
None — all probes passed.
