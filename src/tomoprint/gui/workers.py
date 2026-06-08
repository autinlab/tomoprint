"""Background work: build/export meshes off the GUI thread.

CRITICAL: nothing here touches VTK or Qt widgets. Workers return plain numpy arrays
(:class:`MeshPayload`); the main thread converts them to ``pyvista.PolyData`` and renders.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from PySide6 import QtCore

from tomoprint.io_mrc import write_mesh
from tomoprint.params import GeometryParams, MeshParams
from tomoprint.pipeline import build_mesh_from_heightmap, suggest_bin_factor


@dataclass
class MeshPayload:
    """A VTK-free description of a built mesh, safe to pass between threads."""

    points: np.ndarray  # (N, 3) float32
    faces: np.ndarray  # (M, 3) int64
    scalars: np.ndarray  # (N,) float32 (vertex height in mm)
    diagnostics: dict
    extent_mm: tuple[float, float, float]
    preview: bool


def build_mesh_payload(
    hm01: np.ndarray,
    geo: GeometryParams,
    meshp: MeshParams,
    voxel: float,
    preview_cap: int | None = None,
) -> MeshPayload:
    """Build a relief mesh and return it as plain arrays. With ``preview_cap`` set, the heightmap
    is binned down and smoothing/decimation are skipped for a fast, lower-res preview."""
    preview = False
    if preview_cap is not None:
        bf = suggest_bin_factor(hm01.shape, preview_cap)
        if bf > 1:
            from tomoprint.filters import downsample_heightmap

            hm01 = downsample_heightmap(hm01, bf)
            preview = True
        meshp = replace(
            meshp, taubin_iterations=0, decimate_fraction=None, decimate_target_faces=None
        )

    mesh, diag = build_mesh_from_heightmap(hm01, geo, meshp, voxel)
    points = np.asarray(mesh.vertices, dtype=np.float32)
    return MeshPayload(
        points=points,
        faces=np.asarray(mesh.faces, dtype=np.int64),
        scalars=points[:, 2].copy(),
        diagnostics=diag,
        extent_mm=tuple(float(e) for e in mesh.extents),
        preview=preview,
    )


def export_to_file(
    hm01: np.ndarray,
    geo: GeometryParams,
    meshp: MeshParams,
    voxel: float,
    path: str,
    file_format: str | None,
) -> dict:
    """Build the FULL-resolution mesh (with smoothing/decimation) and write it to disk."""
    mesh, diag = build_mesh_from_heightmap(hm01, geo, meshp, voxel)
    write_mesh(mesh, path, file_format=file_format)
    diag = dict(diag)
    diag["path"] = str(path)
    return diag


class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal(int, object)  # (request_id, result)
    error = QtCore.Signal(int, str)  # (request_id, message)


class FnWorker(QtCore.QRunnable):
    """Runs ``fn(*args)`` on a thread-pool thread and reports the result via signals."""

    def __init__(self, request_id: int, fn, *args) -> None:
        super().__init__()
        self.request_id = request_id
        self._fn = fn
        self._args = args
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self) -> None:  # noqa: D401
        try:
            result = self._fn(*self._args)
        except Exception as exc:  # surface to the UI rather than crash the worker thread
            self.signals.error.emit(self.request_id, f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(self.request_id, result)
