"""tomoprint — convert cryo-ET tomograms (.mrc) into watertight, 3D-printable relief plates.

The :mod:`tomoprint` package exposes a small set of pure functions (no GUI / VTK in the
algorithm layer) that can be driven from the CLI (:mod:`tomoprint.cli`) or the desktop GUI
(:mod:`tomoprint.gui`). The typical entry points are :func:`run_from_file` (load an MRC and
write a mesh) and :func:`run_pipeline` (operate on an in-memory volume).
"""

from tomoprint.exceptions import NonManifoldError, TomoprintError, ValidationError
from tomoprint.heightmap import Heightmap
from tomoprint.params import FilterParams, GeometryParams, MeshParams, ReduceParams
from tomoprint.pipeline import (
    build_mesh_from_heightmap,
    compute_heightmap_2d,
    run_from_file,
    run_pipeline,
)

__version__ = "0.1.0"

__all__ = [
    "ReduceParams",
    "FilterParams",
    "GeometryParams",
    "MeshParams",
    "Heightmap",
    "run_pipeline",
    "run_from_file",
    "compute_heightmap_2d",
    "build_mesh_from_heightmap",
    "TomoprintError",
    "ValidationError",
    "NonManifoldError",
    "__version__",
]
