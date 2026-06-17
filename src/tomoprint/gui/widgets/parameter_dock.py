"""Right dock: grouped parameter controls (Source / Contrast / Relief / Mesh)."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from tomoprint.gui.settings import ReliefSettings
from tomoprint.gui.widgets.labeled_slider import LabeledSlider

_MODES = [
    ("Single slice", "slice"),
    ("Slab mean", "slab_mean"),
    ("Min projection", "min"),
    ("Mean projection", "mean"),
    ("Max projection", "max"),
]
_BINS = [1, 2, 4, 8]
_CROP_SHAPES = [("Rectangle", "rect"), ("Ellipse", "ellipse"), ("Polygon", "polygon")]


class ParameterDock(QtWidgets.QWidget):
    """All tunable controls. Emits ``changed(hm_dirty)`` where ``hm_dirty`` is True when the 2D
    heightmap must be recomputed (source/contrast) and False for geometry/mesh-only changes."""

    changed = QtCore.Signal(bool)
    cropEnable = QtCore.Signal(bool)
    cropShape = QtCore.Signal(str)
    cropZoom = QtCore.Signal(float)
    cropReset = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = False

        # --- SOURCE -----------------------------------------------------------------------
        self.mode = QtWidgets.QComboBox()
        for text, data in _MODES:
            self.mode.addItem(text, data)
        self.index = LabeledSlider("Slice", 0, 0, 0)
        self.half = LabeledSlider("Slab +/-", 0, 100, 0)
        self.bin = QtWidgets.QComboBox()
        for b in _BINS:
            self.bin.addItem(f"{b}x", b)
        source = self._group("Source", [
            self._row("Mode", self.mode), self.index, self.half, self._row("Downsample", self.bin),
        ])

        # --- CONTRAST ---------------------------------------------------------------------
        self.plow = LabeledSlider("Low %", 0.0, 49.0, 1.0, step=0.5, decimals=1)
        self.phigh = LabeledSlider("High %", 51.0, 100.0, 99.0, step=0.5, decimals=1)
        self.sigma = LabeledSlider("Blur σ", 0.0, 10.0, 1.0, step=0.1, decimals=1)
        self.invert = QtWidgets.QCheckBox("Invert (features pop out)")
        contrast = self._group("Contrast", [self.plow, self.phigh, self.sigma, self.invert])

        # --- RELIEF -----------------------------------------------------------------------
        self.footprint = LabeledSlider("Size mm", 20.0, 400.0, 200.0, step=1.0, decimals=1)
        self.relief = LabeledSlider("Relief mm", 0.5, 50.0, 6.0, step=0.5, decimals=1)
        self.base = LabeledSlider("Base mm", 0.5, 20.0, 2.0, step=0.5, decimals=1)
        relief = self._group("Relief (mm)", [self.footprint, self.relief, self.base])

        # --- CROP -------------------------------------------------------------------------
        self.crop_enable = QtWidgets.QCheckBox("Enable crop")
        self.crop_shape = QtWidgets.QComboBox()
        for text, data in _CROP_SHAPES:
            self.crop_shape.addItem(text, data)
        self.crop_zoom = LabeledSlider("Zoom", 1.0, 8.0, 1.0, step=0.1, decimals=1)
        self.crop_reset = QtWidgets.QPushButton("Reset region")
        self.crop_hint = QtWidgets.QLabel(
            "Drag the region on the left. Polygon: double-click to add, right-click to remove."
        )
        self.crop_hint.setWordWrap(True)
        self.crop_hint.setStyleSheet("color:#888; font-size:10px;")
        crop = self._group("Crop", [
            self.crop_enable, self._row("Shape", self.crop_shape), self.crop_zoom,
            self.crop_reset, self.crop_hint,
        ])

        # --- JIGSAW -----------------------------------------------------------------------
        self.jig_enable = QtWidgets.QCheckBox("Cut into puzzle pieces (on export)")
        self.jig_cols = LabeledSlider("Columns", 1, 16, 4)
        self.jig_rows = LabeledSlider("Rows", 1, 16, 3)
        self.jig_tab = LabeledSlider("Tab size", 0.05, 0.45, 0.22, step=0.01, decimals=2)
        self.jig_kerf = LabeledSlider("Kerf mm", 0.0, 2.0, 0.2, step=0.05, decimals=2)
        self.jig_seed = LabeledSlider("Seed", 0, 999, 0)
        self.jig_preview3d = QtWidgets.QCheckBox("Preview pieces in 3D (slower)")
        jigsaw = self._group("Jigsaw", [
            self.jig_enable, self.jig_cols, self.jig_rows, self.jig_tab, self.jig_kerf,
            self.jig_seed, self.jig_preview3d,
        ])

        # --- MESH -------------------------------------------------------------------------
        self.taubin = LabeledSlider("Smooth", 0, 100, 0)
        self.decimate = LabeledSlider("Decimate %", 0, 95, 0)
        mesh = self._group("Mesh", [self.taubin, self.decimate])

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        for grp in (source, contrast, crop, relief, jigsaw, mesh):
            layout.addWidget(grp)
        layout.addStretch(1)

        # wiring: source/contrast => hm dirty; relief/mesh => mesh only
        for w in (self.index, self.half, self.plow, self.phigh, self.sigma):
            w.valueChanged.connect(lambda _v: self._emit(True))
        for w in (self.footprint, self.relief, self.base, self.taubin, self.decimate):
            w.valueChanged.connect(lambda _v: self._emit(False))
        self.mode.currentIndexChanged.connect(self._on_mode_changed)
        self.bin.currentIndexChanged.connect(lambda _i: self._emit(True))
        self.invert.toggled.connect(lambda _b: self._emit(True))

        # crop: enable/shape/zoom/reset drive the panel ROI (handled in MainWindow)
        self.crop_enable.toggled.connect(self._on_crop_enable)
        self.crop_shape.currentIndexChanged.connect(self._on_crop_shape)
        self.crop_zoom.valueChanged.connect(self._on_crop_zoom)
        self.crop_reset.clicked.connect(lambda: self.cropReset.emit())

        # jigsaw: geometry affects the mesh only (and the 2D overlay), not the heightmap
        for w in (self.jig_cols, self.jig_rows, self.jig_tab, self.jig_kerf, self.jig_seed):
            w.valueChanged.connect(lambda _v: self._emit(False))
        self.jig_enable.toggled.connect(lambda _b: self._emit(False))
        self.jig_preview3d.toggled.connect(lambda _b: self._emit(False))

    # ---- helpers -------------------------------------------------------------------------
    @staticmethod
    def _row(label: str, widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lab = QtWidgets.QLabel(label)
        lab.setMinimumWidth(64)
        lay.addWidget(lab)
        lay.addWidget(widget, 1)
        return row

    @staticmethod
    def _group(title: str, widgets: list[QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox(title)
        lay = QtWidgets.QVBoxLayout(box)
        lay.setSpacing(4)
        for w in widgets:
            lay.addWidget(w)
        return box

    def _emit(self, hm_dirty: bool) -> None:
        if not self._loading:
            self.changed.emit(hm_dirty)

    def _on_mode_changed(self, _index: int) -> None:
        self.half.setEnabled(self.mode.currentData() != "slice")
        self._emit(True)

    def _on_crop_enable(self, on: bool) -> None:
        if not self._loading:
            self.cropEnable.emit(on)

    def _on_crop_shape(self, _index: int) -> None:
        if not self._loading:
            self.cropShape.emit(self.crop_shape.currentData())

    def _on_crop_zoom(self, value: float) -> None:
        if not self._loading:
            self.cropZoom.emit(float(value))

    # ---- public API ----------------------------------------------------------------------
    def set_slice_range(self, nz: int) -> None:
        self._loading = True
        self.index.set_maximum(max(0, nz - 1))
        self.index.set_value(nz // 2)
        self.half.set_maximum(max(0, nz))
        self._loading = False

    def write_into(self, s: ReliefSettings) -> None:
        s.mode = self.mode.currentData()
        s.index = int(self.index.value())
        s.half_thickness = int(self.half.value())
        s.bin_factor = int(self.bin.currentData())
        s.pclip_low = float(self.plow.value())
        s.pclip_high = float(self.phigh.value())
        s.sigma = float(self.sigma.value())
        s.invert = self.invert.isChecked()
        s.footprint_mm = float(self.footprint.value())
        s.relief_depth_mm = float(self.relief.value())
        s.base_thickness_mm = float(self.base.value())
        s.taubin_iterations = int(self.taubin.value())
        s.decimate_percent = float(self.decimate.value())
        # crop: only the dock-owned fields (the ROI geometry is written by the source panel)
        s.crop_enabled = self.crop_enable.isChecked()
        s.crop_shape = self.crop_shape.currentData()
        # jigsaw
        s.jigsaw_enabled = self.jig_enable.isChecked()
        s.jigsaw_cols = int(self.jig_cols.value())
        s.jigsaw_rows = int(self.jig_rows.value())
        s.jigsaw_tab = float(self.jig_tab.value())
        s.jigsaw_kerf = float(self.jig_kerf.value())
        s.jigsaw_seed = int(self.jig_seed.value())
        s.jigsaw_preview_3d = self.jig_preview3d.isChecked()

    def read_from(self, s: ReliefSettings) -> None:
        self._loading = True
        self.mode.setCurrentIndex(max(0, self.mode.findData(s.mode)))
        self.index.set_value(s.index if s.index >= 0 else self.index.value())
        self.half.set_value(s.half_thickness)
        self.bin.setCurrentIndex(max(0, self.bin.findData(s.bin_factor)))
        self.plow.set_value(s.pclip_low)
        self.phigh.set_value(s.pclip_high)
        self.sigma.set_value(s.sigma)
        self.invert.setChecked(s.invert)
        self.footprint.set_value(s.footprint_mm)
        self.relief.set_value(s.relief_depth_mm)
        self.base.set_value(s.base_thickness_mm)
        self.taubin.set_value(s.taubin_iterations)
        self.decimate.set_value(s.decimate_percent)
        self.crop_enable.setChecked(s.crop_enabled)
        self.crop_shape.setCurrentIndex(max(0, self.crop_shape.findData(s.crop_shape)))
        self.crop_zoom.set_value(1.0)
        self.jig_enable.setChecked(s.jigsaw_enabled)
        self.jig_cols.set_value(s.jigsaw_cols)
        self.jig_rows.set_value(s.jigsaw_rows)
        self.jig_tab.set_value(s.jigsaw_tab)
        self.jig_kerf.set_value(s.jigsaw_kerf)
        self.jig_seed.set_value(s.jigsaw_seed)
        self.jig_preview3d.setChecked(s.jigsaw_preview_3d)
        self.half.setEnabled(s.mode != "slice")
        self._loading = False
