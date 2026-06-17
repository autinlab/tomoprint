# tomoprint

Turn cryo-ET **tomograms** (`.mrc`) into clean, watertight, 3D-printable **relief plates** —
"moon plate" style, where dense biological features (capsids, cells, viruses) read as **craters**
carved by contrast through depth.

A tomogram is collapsed to a 2D heightmap (a single slice by default, or a slab / min·mean·max
projection), conditioned (denoise, contrast, optional invert), and turned into a solid plate:
a relief top surface + flat base + side walls, guaranteed manifold and watertight so it prints
as-is. Drive it from a scriptable **library + CLI**, or the **desktop GUI** with live sliders and
a 3D preview.

You can also **crop** to a region of interest — rectangle, ellipse, or freehand polygon (the plate
takes that shape) — and optionally **cut the plate into interlocking jigsaw pieces** on export, so
the print is a puzzle you assemble.

```
tomogram (Z,Y,X)  ──reduce──▶  heightmap (Y,X)  ──contrast/invert──▶  z = base + relief·v
                                                                              │
                                          watertight relief plate  ◀──mesh────┘
                                          (relief top + base + walls) ──▶ STL / OBJ / PLY
```

## Install (micromamba)

Base Python 3.14 is too new for the VTK/Qt stack, so use a dedicated `python=3.11` env:

```bash
micromamba create -y -n tomoprint -c conda-forge \
  python=3.11 \
  "numpy>=1.26,<2.3" "scipy>=1.13,<2" "mrcfile>=1.5,<2" "scikit-image>=0.24,<0.27" \
  "vtk>=9.3,<9.7" "pyvista>=0.44,<0.46" "pyvistaqt>=0.11,<0.12" "pyside6>=6.7,<6.10" \
  "pytest>=8" "pytest-cov>=5" "ruff>=0.6"
micromamba run -n tomoprint python -m pip install -e ".[dev]"
```

`pip install -e` also pulls the boolean stack (`shapely`, `manifold3d`, `mapbox-earcut`) used for
shaped crops and the jigsaw cut, plus `fast-simplification` for mesh decimation.

The pure-core extra omits VTK/Qt (`pip install -e ".[test]"`) if you only need the library + CLI.

## Quickstart

```bash
# CLI: middle slice, 200 mm footprint, 6 mm relief, 2 mm base -> STL
micromamba run -n tomoprint tomoprint data/capsid_trim.mrc capsid.stl --report

# Min-intensity projection over +/-5 slices (emphasizes dense capsids), features popped out
micromamba run -n tomoprint tomoprint data/capsid_trim.mrc caps_min.stl \
  --mode min --half-thickness 5 --invert

# Large tomogram: bin x2 to ~256k triangles
micromamba run -n tomoprint tomoprint data/bot_left_trim.mrc bot.stl --bin 2 --report

# Crop to an elliptical region (round plate) centred on a feature
micromamba run -n tomoprint tomoprint data/capsid_trim.mrc disc.stl \
  --crop-shape ellipse --crop-cx 0.5 --crop-cy 0.45 --crop-w 0.6 --crop-h 0.6

# Cut the plate into a 5x4 interlocking jigsaw puzzle (one STL, each piece a separate body)
micromamba run -n tomoprint tomoprint data/capsid_trim.mrc puzzle.stl \
  --jigsaw --jigsaw-cols 5 --jigsaw-rows 4 --jigsaw-kerf 0.2

# Desktop GUI (interactive crop ROI + jigsaw overlay)
micromamba run -n tomoprint tomoprint-gui
```

```python
# Library
from tomoprint import run_from_file, ReduceParams, GeometryParams
mesh, diag = run_from_file(
    "data/capsid_trim.mrc",
    reduce_p=ReduceParams(mode="slice", index=50),
    geo_p=GeometryParams(footprint_mm=200, relief_depth_mm=6, base_thickness_mm=2),
    out="capsid.stl",
)
print(diag)  # {'watertight': True, 'euler_number': 2, 'volume_mm3': ..., 'n_faces': ...}
```

## Parameters

| Group | Option | Default | Meaning |
|-------|--------|---------|---------|
| Source | `--mode` | `slice` | `slice` · `slab_mean` · `min` · `mean` · `max` |
| | `--index` | middle | slice / slab centre |
| | `--half-thickness` | 0 | ± N slices for slab/projection |
| | `--bin` | 1 | integer downsample (simplify + denoise) |
| Contrast | `--sigma` | 1.0 | gaussian blur (px) |
| | `--pclip-low/high` | 1 / 99 | contrast percentile clip |
| | `--invert` | off | flip craters ↔ bumps |
| Relief | `--footprint` | 200 | longest plate side (mm) |
| | `--relief` | 6 | relief depth (mm) |
| | `--base` | 2 | solid base thickness (mm) |
| Crop | `--crop-shape` | off | `rect` · `ellipse` (polygon is GUI-only) |
| | `--crop-cx/cy` | 0.5 | region centre (0–1 of width/height) |
| | `--crop-w/h` | 1.0 | region size (0–1 of footprint) |
| Jigsaw | `--jigsaw` | off | cut the plate into puzzle pieces |
| | `--jigsaw-cols/rows` | 4 / 3 | puzzle grid |
| | `--jigsaw-tab` | 0.22 | tab size (fraction of cell edge) |
| | `--jigsaw-kerf` | 0.2 | gap between pieces (mm) for fit |
| Mesh | `--taubin` | 0 | Taubin smoothing iterations |
| | `--decimate` | off | keep-fraction (0–1) |

Run `tomoprint --help` for the full list. The GUI exposes the same parameters as live sliders.

## Development

```bash
micromamba run -n tomoprint pytest -m "not slow"   # fast unit tests (no VTK/Qt)
micromamba run -n tomoprint pytest -m slow          # real-MRC end-to-end (writes an STL)
micromamba run -n tomoprint ruff check src tests
```

Architecture: a pure algorithm layer (`numpy`/`scipy`/`scikit-image`/`trimesh`, no VTK/Qt) under
`src/tomoprint/`, with `cli.py` and `gui/` as thin frontends that call `pipeline.py`. See
`pyproject.toml` extras `[viz]`/`[gui]`/`[test]`/`[dev]`.
