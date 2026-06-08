"""Left panel: a grayscale view of the current 2D heightmap that feeds the relief."""

from __future__ import annotations

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets


class SourcePanel(QtWidgets.QWidget):
    """Displays the 0..1 heightmap as an aspect-locked grayscale image."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QtGui.QImage | None = None

        self.title = QtWidgets.QLabel("Source heightmap")
        self.title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.view = QtWidgets.QLabel("Open an .mrc tomogram to begin")
        self.view.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.view.setMinimumSize(240, 240)
        self.view.setStyleSheet("background:#101014; color:#888; border:1px solid #333;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.title)
        layout.addWidget(self.view, 1)

    def set_heightmap(self, hm01: np.ndarray) -> None:
        """Render a 0..1 ``(H, W)`` array as a grayscale image (high = light = peaks)."""
        arr = np.clip(hm01, 0.0, 1.0)
        img8 = np.ascontiguousarray((arr * 255).astype(np.uint8))
        h, w = img8.shape
        # keep the buffer alive for the lifetime of the QImage
        self._buffer = img8
        gray = QtGui.QImage.Format.Format_Grayscale8
        self._image = QtGui.QImage(self._buffer.data, w, h, w, gray)
        self._rescale()

    def clear(self) -> None:
        self._image = None
        self.view.setText("Open an .mrc tomogram to begin")

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._image is None:
            return
        pix = QtGui.QPixmap.fromImage(self._image).scaled(
            self.view.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self.view.setPixmap(pix)
