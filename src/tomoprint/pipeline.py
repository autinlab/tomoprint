"""Pipeline orchestration: compose the pure stages into end-to-end runs.

Two composite helpers give the GUI clean caching seams:
``compute_heightmap_2d`` (the cheap 2D tail, recomputed live for the source panel) and
``build_mesh_from_heightmap`` (the expensive mesh tail, run on a worker thread).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from pathlib import Path

import numpy as np

from tomoprint import filters
from tomoprint import mesh as mesh_mod
from tomoprint import reduce as reduce_mod
from tomoprint.heightmap import map_to_height
from tomoprint.io_mrc import load_volume, write_mesh
from tomoprint.params import FilterParams, GeometryParams, MeshParams, ReduceParams

logger = logging.getLogger("tomoprint")

Progress = Callable[[str, float], None]


def _make_reporter(progress: Progress | None) -> Progress:
    """Wrap a progress callback so reported fractions never go backwards (clamped to [0, 1])."""
    last = 0.0

    def report(msg: str, frac: float) -> None:
        nonlocal last
        frac = max(last, min(1.0, float(frac)))
        last = frac
        if progress is not None:
            progress(msg, frac)

    return report


def compute_heightmap_2d(
    volume: np.ndarray, reduce_p: ReduceParams, filt_p: FilterParams
) -> np.ndarray:
    """Cheap 2D tail: reduce -> gaussian -> downsample -> contrast-normalize -> invert.

    Returns a 0..1 float32 ``(H, W)`` array — exactly what feeds :func:`map_to_height` and what
    the GUI shows in its source panel.
    """
    hm = reduce_mod.reduce_to_heightmap(volume, reduce_p)
    hm = filters.gaussian_smooth(hm, filt_p.sigma)
    hm = filters.downsample_heightmap(hm, filt_p.bin_factor)
    hm01 = filters.normalize_contrast(hm, filt_p.pclip_low, filt_p.pclip_high)
    hm01 = filters.apply_invert(hm01, filt_p.invert)
    return hm01


def build_mesh_from_heightmap(
    hm01: np.ndarray,
    geo_p: GeometryParams,
    mesh_p: MeshParams,
    voxel_size_a: float,
    progress: Progress | None = None,
) -> tuple[object, dict]:
    """Expensive tail: map to mm -> build solid -> smooth -> decimate -> verify/repair.

    Returns ``(trimesh.Trimesh, diagnostics)``.
    """
    report = _make_reporter(progress)
    report("building mesh", 0.30)
    hmap = map_to_height(hm01, geo_p, voxel_size_a)
    m = mesh_mod.build_relief_mesh(hmap)

    report("smoothing", 0.70)
    m = mesh_mod.smooth_mesh(m, mesh_p.taubin_iterations)

    report("decimating", 0.80)
    m = mesh_mod.decimate_mesh(m, mesh_p.decimate_fraction, mesh_p.decimate_target_faces)

    report("verifying", 0.95)
    m, diag = mesh_mod.ensure_watertight(m, repair=mesh_p.repair)
    report("done", 1.0)
    logger.info("mesh built: %s", diag)
    return m, diag


def run_pipeline(
    volume: np.ndarray,
    voxel_size_a: float,
    reduce_p: ReduceParams,
    filt_p: FilterParams,
    geo_p: GeometryParams,
    mesh_p: MeshParams,
    progress: Progress | None = None,
) -> tuple[object, dict]:
    """Full in-memory run: 3D volume -> watertight relief mesh + diagnostics."""
    report = _make_reporter(progress)
    report("reducing", 0.05)
    hm01 = compute_heightmap_2d(volume, reduce_p, filt_p)
    report("heightmap ready", 0.20)
    return build_mesh_from_heightmap(hm01, geo_p, mesh_p, voxel_size_a, report)


def run_from_file(
    path: str | Path,
    *,
    reduce_p: ReduceParams | None = None,
    filt_p: FilterParams | None = None,
    geo_p: GeometryParams | None = None,
    mesh_p: MeshParams | None = None,
    out: str | Path | None = None,
    progress: Progress | None = None,
) -> tuple[object, dict]:
    """Load an MRC, run the pipeline, and (optionally) write the mesh. The CLI's call target."""
    reduce_p = reduce_p or ReduceParams()
    filt_p = filt_p or FilterParams()
    geo_p = geo_p or GeometryParams()
    mesh_p = mesh_p or MeshParams()

    volume, header_voxel = load_volume(path)
    voxel = geo_p.voxel_size_a if geo_p.voxel_size_a is not None else header_voxel
    m, diag = run_pipeline(volume, voxel, reduce_p, filt_p, geo_p, mesh_p, progress)
    if out is not None:
        write_mesh(m, out)
    return m, diag


def suggest_bin_factor(yx_shape: tuple[int, int], max_dim: int = 256) -> int:
    """Smallest bin factor so the larger heightmap dimension is <= ``max_dim`` (for previews)."""
    longest = max(yx_shape)
    if longest <= max_dim:
        return 1
    return int(math.ceil(longest / max_dim))


def suggest_export_bin(yx_shape: tuple[int, int], target_top_faces: int = 250_000) -> int:
    """Suggest a bin factor so the top surface stays near ``target_top_faces`` triangles."""
    h, w = yx_shape
    top_faces = 2 * max(1, h - 1) * max(1, w - 1)
    if top_faces <= target_top_faces:
        return 1
    return int(math.ceil(math.sqrt(top_faces / target_top_faces)))
