"""Filesystem IO: read MRC volumes, write meshes. The ONLY algorithm module that touches disk."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from tomoprint.exceptions import ValidationError

logger = logging.getLogger("tomoprint")

MESH_FORMATS: tuple[str, ...] = ("stl", "obj", "ply")


def load_volume(path: str | Path) -> tuple[np.ndarray, float]:
    """Read an MRC file into a C-contiguous ``(Z, Y, X)`` float32 array.

    Returns ``(volume, voxel_size_angstrom)``. A 2D image is promoted to a single-slice
    ``(1, Y, X)`` volume. The voxel size is read from the header (falling back to 1.0 if absent).
    """
    import mrcfile

    path = Path(path)
    if not path.exists():
        raise ValidationError(f"MRC file not found: {path}")

    with mrcfile.open(path, permissive=True, mode="r") as mrc:
        data = mrc.data
        if data is None:
            raise ValidationError(f"MRC file has no data: {path}")
        volume = np.ascontiguousarray(data, dtype=np.float32)
        try:
            voxel_size = float(mrc.voxel_size.x)
        except (AttributeError, TypeError):
            voxel_size = 0.0

    if volume.ndim == 2:
        volume = volume[np.newaxis, ...]
    elif volume.ndim != 3:
        raise ValidationError(f"Expected a 2D or 3D MRC, got {volume.ndim}D array {volume.shape}")

    if not np.isfinite(voxel_size) or voxel_size <= 0:
        logger.warning("MRC %s has no usable voxel size; defaulting to 1.0 A", path.name)
        voxel_size = 1.0

    logger.info("Loaded %s shape=%s (Z,Y,X) voxel=%.3f A", path.name, volume.shape, voxel_size)
    return volume, voxel_size


def write_mesh(mesh, path: str | Path, file_format: str | None = None) -> Path:
    """Export a :class:`trimesh.Trimesh` to STL/OBJ/PLY (inferred from extension if not given)."""
    path = Path(path)
    fmt = (file_format or path.suffix.lstrip(".")).lower()
    if fmt not in MESH_FORMATS:
        raise ValidationError(f"Unsupported mesh format {fmt!r}; choose one of {MESH_FORMATS}")
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(file_obj=str(path), file_type=fmt)
    logger.info("Wrote mesh %s (%d faces)", path, len(mesh.faces))
    return path
