# `data/` — sample inputs and saved presets

`*.mrc`, `*.rec`, `*.map` and `*.stl` are gitignored: they are local samples and outputs, not part of
the repo. The `*.json` presets **are** committed, because each one records the parameters that
produced a plate and the tomogram it was produced from.

Written 2026-08-28, when every preset's `source_path` was checked against disk.

## Presets, and whether their source still exists

| preset | `source_path` resolves? | source |
| --- | --- | --- |
| `capsid_tomogram_puzzle.json` | **yes** | `~/Documents/collabs/salk/pure_cores/cryo_electron_tomography/deconv/Position_3_3_8Apx_trim.mrc` |
| `capsid_tomogram_justin.json` | yes (untracked preset) | `.../deconv/Position_3_3_8.00Apx.mrc` |
| `capsid_trim_test.json` | yes | `data/capsid_trim.mrc`, in this directory |
| `mitochondria_test.json` | **no** | `~/Downloads/YTC009_3_lam11_ts1.mrc_15.83Apx.mrc` |

### `capsid_tomogram_puzzle.json` was repointed, not guessed

Until 2026-08-28 its `source_path` read
`~/Documents/collabs/lyumkis/data/pure_cores/...`, a tree renamed to `collabs/salk/pure_cores/...`
(the `/data/` level went too). The new path was confirmed rather than assumed: the preset's own
`source_dims` of 225 × 1202 × 854 as float32 plus a 1024-byte MRC header comes to exactly
923,858,224 bytes, which is the byte-for-byte size of the file it now points at.

### `mitochondria_test.json`'s source is gone, and cannot be recovered here

It pointed at a file in `~/Downloads`, which no longer exists. Its `source_dims` of 234 × 960 × 682
imply 612,818,944 bytes; **no file of that size exists anywhere** under `~/Documents` or on
`/media/qtallon/BIGDATA`, searched 2026-08-28. So this preset's parameters are still readable and
still valid, but the plate cannot be regenerated from them on this machine.

The path is left as written. It is the historical record of where the preset came from, and
rewriting it to something that resolves would be an invention. If the tomogram turns up, repoint it
and check the size arithmetic above before trusting the match.
