# PB-T5 — install-engine.py probe results

## Probe 1: `--help` exits 0

```
usage: install-engine.py [-h] --library LIBRARY

Copy the engine into a target library and sync engine_version

options:
  -h, --help         show this help message and exit
  --library LIBRARY  Path to target library
```

**Result:** exit code 0 — PASS

## Probe 2: copy + stamp sync

Temp library created with:
- `library.json`: `{"convention_version":"1.0","engine_version":"0.9","name":"t","default_lang":"en","sections":["a"],"extra_asset_root":null}`
- `assemble.py`: empty

Command:
```
python html/slide-library/engine/install-engine.py --library {tmp}
```

Output:
```
copied engine -> {tmp}\assemble.py
engine_version: 0.9 -> 1.0
```

Assertions:
- `{tmp}/assemble.py` byte-equals `html/slide-library/engine/assemble.py` — **True**
- Reloaded `library.json` `engine_version` == engine's `ENGINE_VERSION` ("1.0") — **True**

**Result:** PASS

## Probe 3: missing `library.json` → exit 1

Temp directory with no `library.json`.

Output:
```
ERROR: library.json not found in {tmp}\empty-lib
```

**Result:** exit code 1 — PASS

## git status

```
?? html/slide-library/engine/install-engine.py
```

## Summary

All 3 acceptance criteria pass. The file `html/slide-library/engine/install-engine.py` is the only new file.
