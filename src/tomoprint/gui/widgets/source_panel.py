"""Left panel: the 2D heightmap with an interactive crop ROI and an optional jigsaw overlay.

The panel always shows the *full* heightmap; the crop region (rectangle, ellipse, or polygon) is
drawn on top as an editable item. Dragging the body moves the ROI; dragging a handle resizes it
(box shapes) or moves a vertex (polygon). Edits emit :pyattr:`cropChanged` with normalized
``CropParams`` fields. When jigsaw is enabled, the puzzle cut lines are overlaid (cheap, 2D only).
"""

from __future__ import annotations

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

_HANDLE_FRAC = 0.018  # handle half-size as a fraction of the larger image dimension
_MIN_FRAC = 0.05  # smallest ROI size (fraction of the image), to avoid degenerate crops


class _CropRoiItem(QtWidgets.QGraphicsObject):
    """An editable crop ROI in image-pixel coordinates (item origin == scene origin)."""

    changed = QtCore.Signal()

    def __init__(self, img_w: int, img_h: int) -> None:
        super().__init__()
        self._w = img_w
        self._h = img_h
        self._shape = "rect"
        self._enabled = False
        self._rect = QtCore.QRectF(0, 0, img_w, img_h)
        self._poly: list[QtCore.QPointF] = []
        self._drag: tuple[str, int] | None = None
        self._last = QtCore.QPointF()
        self.setAcceptHoverEvents(True)

    # ---- geometry helpers ----------------------------------------------------------------
    def _hs(self) -> float:
        return max(self._w, self._h) * _HANDLE_FRAC

    def _box_handles(self) -> list[QtCore.QPointF]:
        r = self._rect
        cx, cy = r.center().x(), r.center().y()
        return [
            QtCore.QPointF(r.left(), r.top()), QtCore.QPointF(cx, r.top()),
            QtCore.QPointF(r.right(), r.top()), QtCore.QPointF(r.right(), cy),
            QtCore.QPointF(r.right(), r.bottom()), QtCore.QPointF(cx, r.bottom()),
            QtCore.QPointF(r.left(), r.bottom()), QtCore.QPointF(r.left(), cy),
        ]

    def boundingRect(self) -> QtCore.QRectF:  # noqa: N802 (Qt override)
        return QtCore.QRectF(0, 0, self._w, self._h).adjusted(-self._hs(), -self._hs(),
                                                              self._hs(), self._hs())

    # ---- public API ----------------------------------------------------------------------
    def set_image_size(self, w: int, h: int) -> None:
        # rescale the ROI so its normalized position/size survives a resolution change
        self.prepareGeometryChange()
        if self._w and self._h:
            sx, sy = w / self._w, h / self._h
            self._rect = QtCore.QRectF(
                self._rect.x() * sx, self._rect.y() * sy,
                self._rect.width() * sx, self._rect.height() * sy,
            )
            self._poly = [QtCore.QPointF(p.x() * sx, p.y() * sy) for p in self._poly]
        self._w, self._h = w, h

    def set_from_norm(self, shape: str, cx: float, cy: float, w: float, h: float,
                      polygon: list) -> None:
        """Set the ROI from normalized crop params (no signal emitted)."""
        self.prepareGeometryChange()
        self._shape = shape
        if shape == "polygon" and len(polygon) >= 3:
            self._poly = [QtCore.QPointF(x * self._w, y * self._h) for x, y in polygon]
        else:
            rw, rh = w * self._w, h * self._h
            self._rect = QtCore.QRectF(cx * self._w - rw / 2, cy * self._h - rh / 2, rw, rh)
            self._clamp_rect()
            if len(self._poly) < 3:
                self._poly = self._default_polygon()
        self.update()

    def set_enabled(self, on: bool) -> None:
        self._enabled = on
        self.setVisible(on)
        self.update()

    def set_shape(self, shape: str) -> None:
        self._shape = shape
        if shape == "polygon" and len(self._poly) < 3:
            self._poly = self._default_polygon()
        self.update()
        self.changed.emit()

    def set_zoom(self, zoom: float) -> None:
        """Resize the box ROI symmetrically about its centre (zoom = 1/size)."""
        if self._shape == "polygon":
            return
        z = max(1.0, float(zoom))
        c = self._rect.center()
        w = self._w / z
        h = self._h / z
        self.prepareGeometryChange()
        self._rect = QtCore.QRectF(c.x() - w / 2, c.y() - h / 2, w, h)
        self._clamp_rect()
        self.update()
        self.changed.emit()

    def reset(self) -> None:
        self.prepareGeometryChange()
        self._rect = QtCore.QRectF(0, 0, self._w, self._h)
        self._poly = self._default_polygon()
        self.update()
        self.changed.emit()

    def crop_dict(self) -> dict:
        """Normalized crop parameters derived from the current ROI."""
        if self._shape == "polygon":
            poly = [[p.x() / self._w, p.y() / self._h] for p in self._poly]
            return {"shape": "polygon", "polygon": poly}
        r = self._rect
        return {
            "shape": self._shape,
            "cx": r.center().x() / self._w,
            "cy": r.center().y() / self._h,
            "width": r.width() / self._w,
            "height": r.height() / self._h,
        }

    def outline_scene(self):
        """Shapely polygon of the ROI in scene/pixel coords (for the jigsaw overlay)."""
        from shapely.geometry import Polygon, box

        if self._shape == "polygon":
            return Polygon([(p.x(), p.y()) for p in self._poly])
        r = self._rect
        if self._shape == "ellipse":
            t = np.linspace(0, 2 * np.pi, 97)[:-1]
            xs = r.center().x() + r.width() / 2 * np.cos(t)
            ys = r.center().y() + r.height() / 2 * np.sin(t)
            return Polygon(np.column_stack([xs, ys]))
        return box(r.left(), r.top(), r.right(), r.bottom())

    # ---- internals -----------------------------------------------------------------------
    def _default_polygon(self) -> list[QtCore.QPointF]:
        cx, cy = self._w / 2, self._h / 2
        rx, ry = self._w * 0.35, self._h * 0.35
        return [
            QtCore.QPointF(cx + rx * np.cos(a), cy + ry * np.sin(a))
            for a in np.linspace(0, 2 * np.pi, 6)[:-1]
        ]

    def _clamp_rect(self) -> None:
        minw, minh = self._w * _MIN_FRAC, self._h * _MIN_FRAC
        r = self._rect
        w = min(max(r.width(), minw), self._w)
        h = min(max(r.height(), minh), self._h)
        x = min(max(r.left(), 0.0), self._w - w)
        y = min(max(r.top(), 0.0), self._h - h)
        self._rect = QtCore.QRectF(x, y, w, h)

    def paint(self, painter, option, widget=None) -> None:  # noqa: N802 (Qt override)
        if not self._enabled:
            return
        hs = self._hs()
        pen = QtGui.QPen(QtGui.QColor("#39d4ff"), max(1.0, hs * 0.18))
        pen.setCosmetic(False)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        # dim the area outside the ROI for clarity
        full = QtGui.QPainterPath()
        full.addRect(QtCore.QRectF(0, 0, self._w, self._h))
        inside = QtGui.QPainterPath()
        if self._shape == "polygon":
            inside.addPolygon(QtGui.QPolygonF(self._poly))
            inside.closeSubpath()
        elif self._shape == "ellipse":
            inside.addEllipse(self._rect)
        else:
            inside.addRect(self._rect)
        painter.fillPath(full.subtracted(inside), QtGui.QColor(0, 0, 0, 110))
        painter.drawPath(inside)

        # handles
        painter.setBrush(QtGui.QColor("#ffffff"))
        pts = self._poly if self._shape == "polygon" else self._box_handles()
        for p in pts:
            painter.drawRect(QtCore.QRectF(p.x() - hs, p.y() - hs, 2 * hs, 2 * hs))

    def _hit(self, pos: QtCore.QPointF) -> tuple[str, int] | None:
        hs = self._hs() * 1.6
        pts = self._poly if self._shape == "polygon" else self._box_handles()
        for i, p in enumerate(pts):
            if abs(pos.x() - p.x()) <= hs and abs(pos.y() - p.y()) <= hs:
                return ("vertex" if self._shape == "polygon" else "handle", i)
        if self._shape == "polygon":
            if QtGui.QPolygonF(self._poly).containsPoint(pos, QtCore.Qt.FillRule.OddEvenFill):
                return ("body", -1)
        elif self._rect.contains(pos):
            return ("body", -1)
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if not self._enabled:
            event.ignore()
            return
        if event.button() == QtCore.Qt.MouseButton.RightButton and self._shape == "polygon":
            self._maybe_delete_vertex(event.pos())
            return
        self._drag = self._hit(event.pos())
        self._last = event.pos()
        if self._drag is None:
            event.ignore()
        else:
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self._drag is None:
            return
        pos = event.pos()
        kind, idx = self._drag
        if kind == "body":
            self._move_by(pos - self._last)
        elif kind == "vertex":
            self.prepareGeometryChange()
            self._poly[idx] = self._clamp_point(pos)
        elif kind == "handle":
            self._resize_handle(idx, pos)
        self._last = pos
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self._drag is not None:
            self._drag = None
            self.changed.emit()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self._enabled and self._shape == "polygon":
            self._insert_vertex(event.pos())

    def _clamp_point(self, p: QtCore.QPointF) -> QtCore.QPointF:
        return QtCore.QPointF(min(max(p.x(), 0.0), self._w), min(max(p.y(), 0.0), self._h))

    def _move_by(self, d: QtCore.QPointF) -> None:
        self.prepareGeometryChange()
        if self._shape == "polygon":
            self._poly = [self._clamp_point(p + d) for p in self._poly]
        else:
            self._rect.translate(d)
            self._clamp_rect()

    def _resize_handle(self, idx: int, pos: QtCore.QPointF) -> None:
        r = QtCore.QRectF(self._rect)
        p = self._clamp_point(pos)
        # idx order: TL, T, TR, R, BR, B, BL, L
        if idx in (0, 6, 7):
            r.setLeft(p.x())
        if idx in (2, 3, 4):
            r.setRight(p.x())
        if idx in (0, 1, 2):
            r.setTop(p.y())
        if idx in (4, 5, 6):
            r.setBottom(p.y())
        self.prepareGeometryChange()
        self._rect = r.normalized()
        self._clamp_rect()

    def _insert_vertex(self, pos: QtCore.QPointF) -> None:
        # insert on the nearest edge
        n = len(self._poly)
        best, bi = 1e18, 0
        for i in range(n):
            a, b = self._poly[i], self._poly[(i + 1) % n]
            mid = QtCore.QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            d = (mid - pos).manhattanLength()
            if d < best:
                best, bi = d, i
        self.prepareGeometryChange()
        self._poly.insert(bi + 1, self._clamp_point(pos))
        self.update()
        self.changed.emit()

    def _maybe_delete_vertex(self, pos: QtCore.QPointF) -> None:
        if len(self._poly) <= 3:
            return
        hit = self._hit(pos)
        if hit and hit[0] == "vertex":
            self.prepareGeometryChange()
            del self._poly[hit[1]]
            self.update()
            self.changed.emit()


class SourcePanel(QtWidgets.QWidget):
    """Heightmap view with an interactive crop ROI and an optional jigsaw cut overlay."""

    cropChanged = QtCore.Signal(dict)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._img_w = 1
        self._img_h = 1
        self._buffer: np.ndarray | None = None
        self._jigsaw = None  # JigsawParams or None

        self.title = QtWidgets.QLabel("Source heightmap — open an .mrc to begin")
        self.title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setBackgroundBrush(QtGui.QColor("#101014"))
        self.view.setMinimumSize(240, 240)
        self.view.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        self.view.wheelEvent = self._wheel  # simple zoom

        self._pixmap = self.scene.addPixmap(QtGui.QPixmap())
        self.roi = _CropRoiItem(1, 1)
        self.scene.addItem(self.roi)
        self.roi.changed.connect(self._on_roi_changed)
        self._jig_item = QtWidgets.QGraphicsPathItem()
        self._jig_item.setPen(QtGui.QPen(QtGui.QColor("#ffd23f"), 0))
        self._jig_item.setZValue(5)
        self.scene.addItem(self._jig_item)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.title)
        layout.addWidget(self.view, 1)

    # ---- display -------------------------------------------------------------------------
    def set_heightmap(self, hm01: np.ndarray) -> None:
        """Render a 0..1 ``(H, W)`` array as grayscale (high = light = peaks)."""
        arr = np.clip(hm01, 0.0, 1.0)
        self._buffer = np.ascontiguousarray((arr * 255).astype(np.uint8))
        h, w = self._buffer.shape
        gray = QtGui.QImage.Format.Format_Grayscale8
        image = QtGui.QImage(self._buffer.data, w, h, w, gray)
        self._pixmap.setPixmap(QtGui.QPixmap.fromImage(image))
        if (w, h) != (self._img_w, self._img_h):
            self._img_w, self._img_h = w, h
            self.roi.set_image_size(w, h)
            self.scene.setSceneRect(0, 0, w, h)
            self._fit()
        self._refresh_jigsaw()

    def clear(self) -> None:
        self._pixmap.setPixmap(QtGui.QPixmap())
        self._jig_item.setPath(QtGui.QPainterPath())

    # ---- crop controls (driven by the parameter dock) ------------------------------------
    def set_crop_enabled(self, on: bool) -> None:
        self.roi.set_enabled(on)
        self._on_roi_changed()

    def set_crop_shape(self, shape: str) -> None:
        self.roi.set_shape(shape)

    def set_crop_zoom(self, zoom: float) -> None:
        self.roi.set_zoom(zoom)

    def reset_crop(self) -> None:
        self.roi.reset()

    def apply_crop_settings(self, enabled: bool, shape: str, cx: float, cy: float,
                            w: float, h: float, polygon: list) -> None:
        """Restore the full ROI state from settings/presets quietly (no ``cropChanged``)."""
        self.roi.set_enabled(enabled)
        self.roi.set_from_norm(shape, cx, cy, w, h, polygon)
        self._refresh_jigsaw()

    def set_jigsaw(self, params) -> None:
        """``params`` is a JigsawParams (enabled) or None to clear the overlay."""
        self._jigsaw = params if (params is not None and params.enabled) else None
        self._refresh_jigsaw()

    # ---- internals -----------------------------------------------------------------------
    def _on_roi_changed(self) -> None:
        self.cropChanged.emit(self.roi.crop_dict())
        self._refresh_jigsaw()

    def _refresh_jigsaw(self) -> None:
        if self._jigsaw is None or self._buffer is None:
            self._jig_item.setPath(QtGui.QPainterPath())
            return
        from dataclasses import replace

        from tomoprint import jigsaw as jigsaw_mod

        if self.roi._enabled:
            outline = self.roi.outline_scene()
        else:
            from shapely.geometry import box

            outline = box(0, 0, self._img_w, self._img_h)
        try:
            polys = jigsaw_mod.piece_polygons(outline, replace(self._jigsaw, kerf_mm=0.0))
        except Exception:
            self._jig_item.setPath(QtGui.QPainterPath())
            return
        path = QtGui.QPainterPath()
        for poly in polys:
            xs, ys = poly.exterior.coords.xy
            qpoly = QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in zip(xs, ys, strict=True)])
            path.addPolygon(qpoly)
        self._jig_item.setPath(path)

    def _fit(self) -> None:
        if self._img_w > 1:
            self.view.fitInView(self.scene.sceneRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)

    def _wheel(self, event: QtGui.QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.view.scale(factor, factor)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._fit()
