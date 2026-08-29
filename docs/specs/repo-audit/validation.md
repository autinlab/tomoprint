# Repo audit — 2026-08-28

Written by a `/root-route` crossing from `scripps-rr`, which read **every file in this repo** —
syntax, imports, configs, markdown links, and every path referenced by anything. This is the record
of what was checked so the next person does not repeat it.

## Verdict: passes

- **64 tests pass** in the `tomoprint` env; `tomoprint --help` works. `environment.yml` matches the
  live environment, which is the only repo here where that was already true.
- All 36 Python files' imports resolve. Clean on every mechanical check.

## What was broken, and fixed

`data/capsid_tomogram_puzzle.json`'s `source_path` pointed into
`~/Documents/collabs/lyumkis/data/...`, a tree renamed to `collabs/salk/pure_cores/...`. Repointed —
and **confirmed rather than assumed**: the preset's own `source_dims` of 225 × 1202 × 854 as float32
plus a 1024-byte MRC header comes to exactly 923,858,224 bytes, the byte-for-byte size of the file it
now names.

`data/README.md` was added recording which presets' sources survive.

## Left open

`data/mitochondria_test.json`'s source is gone everywhere: it pointed into `~/Downloads`, and no file
of its implied 612,818,944 bytes exists under `~/Documents` or on BIGDATA. The path is left as
written, because it is the historical record and rewriting it would be an invention.
