"""Map a normalized 0..1 heightmap to physical millimetre heights for meshing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tomoprint.exceptions import ValidationError
from tomoprint.params import GeometryParams


@dataclass(slots=True)
class Heightmap:
    """A physical heightmap ready to be meshed.

    ``z`` is an ``(H, W)`` float32 array of surface heights in millimetres (already including
    the base thickness, so ``z`` ranges over ``[base, base + relief_depth]``). ``dx_mm`` /
    ``dy_mm`` are the physical spacings between columns (X) and rows (Y).
    """

    z: np.ndarray
    dx_mm: float
    dy_mm: float
    base_thickness_mm: float

    @property
    def shape(self) -> tuple[int, int]:
        return self.z.shape

    @property
    def extent_mm(self) -> tuple[float, float]:
        """Physical (X, Y) extent of the plate footprint in millimetres."""
        h, w = self.z.shape
        return ((w - 1) * self.dx_mm, (h - 1) * self.dy_mm)


def map_to_height(hm01: np.ndarray, geo: GeometryParams, voxel_size_a: float) -> Heightmap:
    """Map a 0..1 heightmap to physical heights and compute the in-plane spacing.

    Heights: ``z = base_thickness + relief_depth * hm01``. The longest in-plane side of the
    plate is scaled to ``geo.footprint_mm`` with the aspect ratio preserved (source voxels are
    isotropic, so pixels are square). ``voxel_size_a`` is retained for metadata only.
    """
    if hm01.ndim != 2:
        raise ValidationError(f"map_to_height expects a 2D heightmap, got {hm01.ndim}D")
    h, w = hm01.shape
    if h < 2 or w < 2:
        raise ValidationError(f"heightmap too small to mesh: {hm01.shape}")

    z = geo.base_thickness_mm + geo.relief_depth_mm * hm01.astype(np.float32, copy=False)

    # Pixel pitch so the longest VERTEX span equals footprint_mm exactly (square pixels).
    denom = max(w, h) - 1
    pitch = geo.footprint_mm / denom
    return Heightmap(
        z=np.ascontiguousarray(z, dtype=np.float32),
        dx_mm=pitch,
        dy_mm=pitch,
        base_thickness_mm=geo.base_thickness_mm,
    )
