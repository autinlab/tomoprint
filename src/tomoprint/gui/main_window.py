"""The tomoprint main window: toolbar, 2D|3D split, parameter dock, status bar, and wiring."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from tomoprint.gui.controller import Controller
from tomoprint.gui.settings import ReliefSettings
from tomoprint.gui.widgets.parameter_dock import ParameterDock
from tomoprint.gui.widgets.relief_viewport import ReliefViewport
from tomoprint.gui.widgets.source_panel import SourcePanel
from tomoprint.io_mrc import load_volume

_MRC_FILTER = "MRC volumes (*.mrc *.mrcs *.rec *.map);;All files (*)"
_MESH_FILTER = "STL (*.stl);;OBJ (*.obj);;PLY (*.ply)"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("tomoprint")
        self.resize(1280, 820)

        self.settings = ReliefSettings()
        self.controller = Controller(self)
        self._src_name = ""
        self._dims = ()
        self._voxel = 0.0

        self.source = SourcePanel()
        self.viewport = ReliefViewport()
        self.dock_widget = ParameterDock()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self.source)
        splitter.addWidget(self.viewport)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        self.setCentralWidget(splitter)

        dock = QtWidgets.QDockWidget("Parameters", self)
        dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.dock_widget)
        scroll.setMinimumWidth(320)
        dock.setWidget(scroll)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self._build_toolbar()
        self._build_statusbar()
        self._wire()

    # ---- construction --------------------------------------------------------------------
    def _build_toolbar(self) -> None:
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        style = self.style()

        def act(icon, text, slot):
            a = QtGui.QAction(style.standardIcon(icon), text, self)
            a.triggered.connect(slot)
            tb.addAction(a)
            return a

        SP = QtWidgets.QStyle.StandardPixmap
        act(SP.SP_DialogOpenButton, "Open MRC", self._open_mrc)
        self._export_action = act(SP.SP_DialogSaveButton, "Export mesh", self._export_mesh)
        self._export_action.setEnabled(False)
        tb.addSeparator()
        act(SP.SP_DialogResetButton, "Load preset", self._load_preset)
        act(SP.SP_DialogApplyButton, "Save preset", self._save_preset)
        tb.addSeparator()
        act(SP.SP_BrowserReload, "Reset view", self.viewport.reset_view)
        act(SP.SP_ArrowUp, "Top view", self.viewport.top_view)
        edl = QtGui.QAction("EDL", self)
        edl.setCheckable(True)
        edl.setChecked(True)
        edl.setToolTip("Eye-dome lighting (depth shading)")
        edl.triggered.connect(lambda: self.viewport.toggle_edl())
        tb.addAction(edl)

    def _build_statusbar(self) -> None:
        self.status_label = QtWidgets.QLabel("Open an .mrc tomogram to begin.")
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setFixedWidth(120)
        self.progress.setVisible(False)
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.progress)

    def _wire(self) -> None:
        self.dock_widget.changed.connect(self._on_params_changed)
        self.dock_widget.cropEnable.connect(self._on_crop_enable)
        self.dock_widget.cropShape.connect(self._on_crop_shape)
        self.dock_widget.cropZoom.connect(self.source.set_crop_zoom)
        self.dock_widget.cropReset.connect(self.source.reset_crop)
        self.source.cropChanged.connect(self._on_crop_changed)
        self.controller.heightmapReady.connect(self.source.set_heightmap)
        self.controller.meshReady.connect(self._on_mesh_ready)
        self.controller.busyChanged.connect(self.progress.setVisible)
        self.controller.errorOccurred.connect(self._on_error)
        self.controller.exportFinished.connect(self._on_export_finished)

    # ---- slots ---------------------------------------------------------------------------
    def _on_params_changed(self, hm_dirty: bool) -> None:
        self.dock_widget.write_into(self.settings)
        self._refresh_jigsaw_overlay()
        self.controller.update_settings(self.settings, hm_dirty)

    def _refresh_jigsaw_overlay(self) -> None:
        jig = self.settings.jigsaw_params() if self.settings.jigsaw_enabled else None
        self.source.set_jigsaw(jig)

    # ---- crop wiring ---------------------------------------------------------------------
    def _on_crop_enable(self, on: bool) -> None:
        self.settings.crop_enabled = on
        self.source.set_crop_enabled(on)  # emits cropChanged -> rebuild

    def _on_crop_shape(self, shape: str) -> None:
        self.settings.crop_shape = shape
        self.source.set_crop_shape(shape)  # emits cropChanged -> rebuild

    def _on_crop_changed(self, d: dict) -> None:
        s = self.settings
        s.crop_shape = d.get("shape", s.crop_shape)
        if d.get("shape") == "polygon":
            s.crop_polygon = d.get("polygon", [])
        else:
            s.crop_cx, s.crop_cy = d["cx"], d["cy"]
            s.crop_w, s.crop_h = d["width"], d["height"]
        if self.controller.has_volume():
            self.controller.update_settings(s, hm_dirty=True)

    def _open_mrc(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open tomogram", "", _MRC_FILTER)
        if not path:
            return
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        try:
            volume, voxel = load_volume(path)
        except Exception as exc:
            QtWidgets.QApplication.restoreOverrideCursor()
            self._on_error(f"Could not open {Path(path).name}: {exc}")
            return
        QtWidgets.QApplication.restoreOverrideCursor()

        nz = volume.shape[0]  # axis 0 is Z
        self.dock_widget.set_slice_range(nz)
        yx = (volume.shape[1], volume.shape[2])
        if max(yx) > 512:  # auto-suggest binning for large tomograms
            self.dock_widget.bin.setCurrentIndex(self.dock_widget.bin.findData(2))
        self.dock_widget.write_into(self.settings)

        self._src_name = Path(path).name
        self._dims = tuple(volume.shape)
        self._voxel = voxel
        self._export_action.setEnabled(True)
        self._sync_crop_panel()
        self.controller.set_volume(volume, voxel, path, self.settings)

    def _sync_crop_panel(self) -> None:
        s = self.settings
        self.source.apply_crop_settings(
            s.crop_enabled, s.crop_shape, s.crop_cx, s.crop_cy, s.crop_w, s.crop_h, s.crop_polygon
        )
        self._refresh_jigsaw_overlay()

    def _on_mesh_ready(self, payload) -> None:
        d = payload.diagnostics
        x, y, z = payload.extent_mm
        wt = "● watertight" if d.get("watertight") else "○ NOT watertight"
        tag = "  [preview]" if payload.preview else ""
        self.status_label.setText(
            f"{self._src_name}  |  {self._dims[2]}×{self._dims[1]}×{self._dims[0]} @ "
            f"{self._voxel:.1f} Å  |  {x:.1f} × {y:.1f} × {z:.1f} mm  |  "
            f"Δ {d.get('n_faces', 0):,}  |  {wt}{tag}"
        )
        self.viewport.set_payload(payload)

    def _export_mesh(self) -> None:
        suggested = (Path(self._src_name).stem or "relief") + ".stl"
        path, selected = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export mesh", suggested, _MESH_FILTER
        )
        if not path:
            return
        p = Path(path)
        fmt = p.suffix.lstrip(".").lower()
        if fmt not in ("stl", "obj", "ply"):
            fmt = "obj" if "obj" in selected else "ply" if "ply" in selected else "stl"
            p = p.with_suffix("." + fmt)
        self.status_label.setText(f"Exporting {p.name} (full resolution)…")
        self.controller.export(str(p), fmt)

    def _on_export_finished(self, diag: dict) -> None:
        wt = "watertight" if diag.get("watertight") else "NOT watertight (check before printing)"
        self.status_label.setText(
            f"Exported {Path(diag['path']).name}  |  {diag.get('n_faces', 0):,} faces  |  {wt}"
        )

    def _save_preset(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save preset", "preset.tomoprint.json", "JSON (*.json)"
        )
        if not path:
            return
        self.dock_widget.write_into(self.settings)
        self.settings.to_json(path)
        self.status_label.setText(f"Saved preset {Path(path).name}")

    def _load_preset(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load preset", "", "JSON (*.json)")
        if not path:
            return
        loaded = ReliefSettings.from_json(path)
        # keep current source metadata; clamp slice to the loaded volume
        if self._dims:
            loaded.index = min(max(0, loaded.index), self._dims[0] - 1)
        loaded.source_path = self.settings.source_path
        loaded.source_dims = self.settings.source_dims
        loaded.voxel_size_a = self.settings.voxel_size_a
        self.settings = loaded
        self.dock_widget.read_from(self.settings)
        self._sync_crop_panel()
        self.status_label.setText(f"Loaded preset {Path(path).name}")
        if self.controller.has_volume():
            self.controller.update_settings(self.settings, hm_dirty=True)

    def _on_error(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)
        QtWidgets.QMessageBox.warning(self, "tomoprint", message)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802 (Qt override)
        self.controller.pool.clear()
        self.viewport.cleanup()
        super().closeEvent(event)
