"""Mediates between the widgets and the core pipeline: caching, debouncing, threaded rebuilds.

Owns the loaded volume + cached 2D heightmap and runs the expensive mesh build on a thread pool
with single-flight coalescing so the UI never freezes and stale results are dropped.
"""

from __future__ import annotations

import numpy as np
from PySide6 import QtCore

from tomoprint.gui.settings import ReliefSettings
from tomoprint.gui.workers import FnWorker, build_mesh_payload, export_to_file
from tomoprint.pipeline import compute_heightmap_2d

PREVIEW_CAP = 224  # max heightmap dimension for the live preview; full-res only on export


class Controller(QtCore.QObject):
    heightmapReady = QtCore.Signal(object)  # np.ndarray (0..1)
    meshReady = QtCore.Signal(object)  # MeshPayload
    busyChanged = QtCore.Signal(bool)
    errorOccurred = QtCore.Signal(str)
    exportFinished = QtCore.Signal(object)  # diagnostics dict

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = ReliefSettings()
        self._volume: np.ndarray | None = None
        self._voxel = 1.0
        self._hm01: np.ndarray | None = None
        self._hm_dirty = True

        self.pool = QtCore.QThreadPool.globalInstance()
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._dispatch)

        self._req = 0
        self._inflight = 0
        self._running = False
        self._pending = False
        self._busy = 0

    def has_volume(self) -> bool:
        return self._volume is not None

    def set_volume(self, volume: np.ndarray, voxel: float, path: str, settings: ReliefSettings):
        self.settings = settings
        self.settings.source_path = str(path)
        self.settings.source_dims = list(volume.shape)
        self.settings.voxel_size_a = float(voxel)
        self._volume = volume
        self._voxel = voxel
        self._hm_dirty = True
        self._dispatch()

    def update_settings(self, settings: ReliefSettings, hm_dirty: bool) -> None:
        self.settings = settings
        self._hm_dirty = self._hm_dirty or hm_dirty
        self._timer.start()

    # ---- internal ------------------------------------------------------------------------
    def _set_busy(self, delta: int) -> None:
        self._busy = max(0, self._busy + delta)
        self.busyChanged.emit(self._busy > 0)

    def _ensure_heightmap(self) -> bool:
        if not self._hm_dirty and self._hm01 is not None:
            return True
        try:
            self._hm01 = compute_heightmap_2d(
                self._volume, self.settings.reduce_params(), self.settings.filter_params()
            )
        except Exception as exc:
            self.errorOccurred.emit(f"{type(exc).__name__}: {exc}")
            return False
        self._hm_dirty = False
        self.heightmapReady.emit(self._hm01)
        return True

    def _dispatch(self) -> None:
        if self._volume is None:
            return
        if self._running:
            self._pending = True
            return
        if not self._ensure_heightmap():
            return

        self._req += 1
        self._inflight = self._req
        self._running = True
        self._set_busy(1)
        worker = FnWorker(
            self._inflight, build_mesh_payload, self._hm01,
            self.settings.geometry_params(), self.settings.mesh_params(), self._voxel, PREVIEW_CAP,
        )
        worker.signals.finished.connect(self._on_preview_finished)
        worker.signals.error.connect(self._on_preview_error)
        self.pool.start(worker)

    @QtCore.Slot(int, object)
    def _on_preview_finished(self, rid: int, payload) -> None:
        self._running = False
        self._set_busy(-1)
        if rid == self._inflight:
            self.meshReady.emit(payload)
        if self._pending:
            self._pending = False
            self._dispatch()

    @QtCore.Slot(int, str)
    def _on_preview_error(self, rid: int, msg: str) -> None:
        self._running = False
        self._set_busy(-1)
        self.errorOccurred.emit(msg)
        if self._pending:
            self._pending = False
            self._dispatch()

    # ---- export (full resolution, off-thread) --------------------------------------------
    def export(self, path: str, file_format: str | None) -> None:
        if self._volume is None or not self._ensure_heightmap():
            self.errorOccurred.emit("Nothing to export yet — open a tomogram first.")
            return
        self._req += 1
        self._set_busy(1)
        worker = FnWorker(
            self._req, export_to_file, self._hm01,
            self.settings.geometry_params(), self.settings.mesh_params(), self._voxel,
            str(path), file_format,
        )
        worker.signals.finished.connect(self._on_export_finished)
        worker.signals.error.connect(self._on_export_error)
        self.pool.start(worker)

    @QtCore.Slot(int, object)
    def _on_export_finished(self, rid: int, diag) -> None:
        self._set_busy(-1)
        self.exportFinished.emit(diag)

    @QtCore.Slot(int, str)
    def _on_export_error(self, rid: int, msg: str) -> None:
        self._set_busy(-1)
        self.errorOccurred.emit(f"Export failed: {msg}")
