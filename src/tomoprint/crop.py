"""Crop the heightmap footprint to a rectangular/elliptical/polygonal region of interest.

Pure numpy/skimage/shapely — no VTK or Qt. The crop is a 2D operation on the reduced (Y, X)
heightmap. A ``rect`` crop just slices the array; ``ellipse``/``polygon`` additionally yield a
shape *mask* (for shape-aware contrast) and an *outline polygon in mm* that the mesh layer
boolean-cuts the relief solid against, so the printed plate takes the cropped shape.

All geometry derives from :func:`crop_bbox_norm` so the result is consistent across resolutions.
"""

from __future__ import annotations

import numpy as np

from tomoprint.params import CropParams


def _relative_polygon(p: CropParams) -> np.ndarray:
    """Polygon vertices remapped into the crop's own bounding box, as ``(N, 2)`` in [0, 1]."""
    poly = np.asarray(p.polygon, dtype=np.float64)
    x0, y0, x1, y1 = _polygon_bounds(poly)
    w = max(x1 - x0, 1e-9)
    h = max(y1 - y0, 1e-9)
    rel = np.column_stack([(poly[:, 0] - x0) / w, (poly[:, 1] - y0) / h])
    return rel


def _polygon_bounds(poly: np.ndarray) -> tuple[float, float, float, float]:
    return (
        float(poly[:, 0].min()),
        float(poly[:, 1].min()),
        float(poly[:, 0].max()),
        float(poly[:, 1].max()),
    )


def crop_bbox_norm(p: CropParams) -> tuple[float, float, float, float]:
    """Normalized ``(x0, y0, x1, y1)`` crop bounding box in [0, 1] (the single source of truth).

    Rect/ellipse: the box centred at ``(cx, cy)`` of size ``(width, height)``, clamped to [0, 1].
    Polygon: the bounding box of the polygon vertices.
    """
    if p.shape == "polygon":
        x0, y0, x1, y1 = _polygon_bounds(np.asarray(p.polygon, dtype=np.float64))
    else:
        x0 = p.cx - p.width / 2.0
        x1 = p.cx + p.width / 2.0
        y0 = p.cy - p.height / 2.0
        y1 = p.cy + p.height / 2.0
    x0, x1 = max(0.0, min(x0, x1)), min(1.0, max(x0, x1))
    y0, y1 = max(0.0, min(y0, y1)), min(1.0, max(y0, y1))
    return (x0, y0, x1, y1)


def _bbox_pixels(p: CropParams, h: int, w: int) -> tuple[int, int, int, int]:
    """Pixel ``(r0, r1, c0, c1)`` for the crop bbox in an ``(h, w)`` array (>=2 px per side)."""
    x0, y0, x1, y1 = crop_bbox_norm(p)
    c0 = int(np.floor(x0 * w))
    c1 = int(np.ceil(x1 * w))
    r0 = int(np.floor(y0 * h))
    r1 = int(np.ceil(y1 * h))
    c0 = max(0, min(c0, w - 2))
    r0 = max(0, min(r0, h - 2))
    c1 = max(c0 + 2, min(c1, w))
    r1 = max(r0 + 2, min(r1, h))
    return (r0, r1, c0, c1)


def crop_heightmap(hm: np.ndarray, p: CropParams) -> np.ndarray:
    """Slice ``hm`` (H, W) to the crop's bounding box. ``p.enabled`` False is a no-op."""
    if not p.enabled:
        return hm
    h, w = hm.shape
    r0, r1, c0, c1 = _bbox_pixels(p, h, w)
    return np.ascontiguousarray(hm[r0:r1, c0:c1])


def shape_mask(p: CropParams, h: int, w: int) -> np.ndarray | None:
    """Boolean in-shape mask for an ``(h, w)`` cropped array, or ``None`` for rect/disabled.

    The mask spans the full cropped array (the bounding box); ``True`` is inside the shape.
    """
    if not p.enabled or p.shape == "rect":
        return None
    if p.shape == "ellipse":
        yy, xx = np.mgrid[0:h, 0:w]
        # ellipse inscribed in the [0, w-1] x [0, h-1] box
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        rx, ry = max(cx, 1e-9), max(cy, 1e-9)
        return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
    # polygon
    from skimage.draw import polygon as sk_polygon

    rel = _relative_polygon(p)
    cc = np.clip(rel[:, 0] * (w - 1), 0, w - 1)
    rr = np.clip(rel[:, 1] * (h - 1), 0, h - 1)
    mask = np.zeros((h, w), dtype=bool)
    fr, fc = sk_polygon(rr, cc, shape=(h, w))
    mask[fr, fc] = True
    return mask


def outline_polygon_mm(p: CropParams, hm_shape: tuple[int, int], dx_mm: float, dy_mm: float):
    """The plate outline in mm for the boolean cut, or ``None`` (rect / disabled => no cut).

    The mm extent matches :func:`tomoprint.mesh.build_relief_mesh`, whose vertex grid spans
    ``[0, (w-1)*dx] x [0, (h-1)*dy]``.
    """
    if p is None or not p.enabled or p.shape == "rect":
        return None
    from shapely.geometry import Polygon

    h, w = hm_shape
    ex, ey = (w - 1) * dx_mm, (h - 1) * dy_mm
    if p.shape == "ellipse":
        t = np.linspace(0.0, 2.0 * np.pi, 129)[:-1]
        xs = ex / 2.0 * (1.0 + np.cos(t))
        ys = ey / 2.0 * (1.0 + np.sin(t))
        poly = Polygon(np.column_stack([xs, ys]))
    else:
        rel = _relative_polygon(p)
        poly = Polygon(np.column_stack([rel[:, 0] * ex, rel[:, 1] * ey]))
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly
