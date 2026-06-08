"""Center panel: an embedded pyvista 3D viewport showing the live relief mesh.

All VTK/pyvista interaction happens here, on the GUI/main thread only.
"""

from __future__ import annotations

import numpy as np
from PySide6 import QtWidgets


class ReliefViewport(QtWidgets.QWidget):
    """Hosts a :class:`pyvistaqt.QtInteractor` and renders :class:`MeshPayload` arrays."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        from pyvistaqt import QtInteractor

        self.plotter = QtInteractor(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plotter)

        self.plotter.set_background("white", top="lightsteelblue")
        self.plotter.add_axes()
        self._actor = None
        self._first = True
        self._edl = True
        try:
            self.plotter.enable_eye_dome_lighting()  # crisp crater depth perception
        except Exception:
            self._edl = False

    def set_payload(self, payload) -> None:
        """Replace the displayed mesh, preserving the camera after the first load."""
        import pyvista as pv

        n = len(payload.faces)
        cells = np.empty((n, 4), dtype=np.int64)
        cells[:, 0] = 3
        cells[:, 1:] = payload.faces
        poly = pv.PolyData(payload.points, cells.ravel())
        poly["height (mm)"] = payload.scalars

        camera = None if self._first else self.plotter.camera_position
        if self._actor is not None:
            self.plotter.remove_actor(self._actor)
        self._actor = self.plotter.add_mesh(
            poly,
            scalars="height (mm)",
            cmap="gray",
            smooth_shading=True,
            specular=0.15,
            show_scalar_bar=True,
            reset_camera=self._first,
        )
        if self._first:
            self.plotter.view_isometric()
            self._first = False
        elif camera is not None:
            self.plotter.camera_position = camera
        self.plotter.render()

    def reset_view(self) -> None:
        self.plotter.reset_camera()
        self.plotter.view_isometric()
        self.plotter.render()

    def top_view(self) -> None:
        self.plotter.view_xy()
        self.plotter.render()

    def toggle_edl(self) -> bool:
        self._edl = not self._edl
        if self._edl:
            self.plotter.enable_eye_dome_lighting()
        else:
            self.plotter.disable_eye_dome_lighting()
        self.plotter.render()
        return self._edl

    def cleanup(self) -> None:
        """Finalize the VTK render window deterministically (call from the window's closeEvent)."""
        try:
            self.plotter.close()
        except Exception:
            pass
