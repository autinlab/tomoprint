"""Parameter dataclasses shared by the core pipeline, CLI, and GUI.

These frozen dataclasses are the single source of truth for defaults and validation. The CLI
builds them from command-line options; the GUI binds widgets to their fields. Validation runs
in ``__post_init__`` and raises :class:`~tomoprint.exceptions.ValidationError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tomoprint.exceptions import ValidationError

ReduceMode = Literal["slice", "slab_mean", "min", "mean", "max"]
REDUCE_MODES: tuple[str, ...] = ("slice", "slab_mean", "min", "mean", "max")
MeshBackend = Literal["trimesh", "pyvista"]
MESH_BACKENDS: tuple[str, ...] = ("trimesh", "pyvista")
CropShape = Literal["rect", "ellipse", "polygon"]
CROP_SHAPES: tuple[str, ...] = ("rect", "ellipse", "polygon")


@dataclass(frozen=True, slots=True)
class ReduceParams:
    """How the 3D volume (Z, Y, X) is collapsed to a 2D (Y, X) heightmap.

    ``mode="slice"`` with ``half_thickness=0`` is a single slice. Any mode with a non-zero
    ``half_thickness`` operates on the slab ``[index - N, index + N]`` (clamped to bounds).
    """

    mode: ReduceMode = "slice"
    index: int = -1  # slice centre; -1 => middle slice (resolved against the axis length)
    half_thickness: int = 0  # +/- N slices around ``index``
    axis: int = 0  # axis to collapse in the (Z, Y, X) array; 0 => collapse Z (default)

    def __post_init__(self) -> None:
        if self.mode not in REDUCE_MODES:
            raise ValidationError(f"mode must be one of {REDUCE_MODES}, got {self.mode!r}")
        if self.half_thickness < 0:
            raise ValidationError(f"half_thickness must be >= 0, got {self.half_thickness}")
        if self.axis not in (0, 1, 2):
            raise ValidationError(f"axis must be 0, 1, or 2, got {self.axis}")


@dataclass(frozen=True, slots=True)
class FilterParams:
    """2D heightmap conditioning: denoise, downsample, contrast, invert."""

    sigma: float = 1.0  # gaussian sigma in heightmap pixels; 0 disables
    bin_factor: int = 1  # integer block-mean downsample; 1 disables
    pclip_low: float = 1.0  # low percentile for contrast clip
    pclip_high: float = 99.0  # high percentile for contrast clip
    invert: bool = False  # flip so low-value features pop OUT instead of being engraved

    def __post_init__(self) -> None:
        if self.sigma < 0:
            raise ValidationError(f"sigma must be >= 0, got {self.sigma}")
        if self.bin_factor < 1:
            raise ValidationError(f"bin_factor must be >= 1, got {self.bin_factor}")
        if not (0.0 <= self.pclip_low < self.pclip_high <= 100.0):
            raise ValidationError(
                "require 0 <= pclip_low < pclip_high <= 100, got "
                f"({self.pclip_low}, {self.pclip_high})"
            )


@dataclass(frozen=True, slots=True)
class CropParams:
    """A 2D region-of-interest applied to the heightmap footprint (the (Y, X) plane).

    Coordinates are normalized fractions in ``[0, 1]`` relative to the *full* reduced heightmap,
    so a crop survives changes to binning/resolution. For ``rect``/``ellipse`` the region is the
    axis-aligned box centred at ``(cx, cy)`` with size ``(width, height)``; the ellipse is
    inscribed in that box. For ``polygon`` the region is the bounding box of ``polygon`` and the
    outline is the polygon itself. A non-``rect`` shape yields a *shaped* plate (the relief solid
    is boolean-cut to the outline); ``rect`` is a plain rectangular crop with no boolean.
    """

    enabled: bool = False
    shape: CropShape = "rect"
    cx: float = 0.5
    cy: float = 0.5
    width: float = 1.0
    height: float = 1.0
    polygon: tuple[tuple[float, float], ...] = ()  # normalized-to-full (x, y) vertices

    def __post_init__(self) -> None:
        if self.shape not in CROP_SHAPES:
            raise ValidationError(f"shape must be one of {CROP_SHAPES}, got {self.shape!r}")
        for name in ("cx", "cy", "width", "height"):
            v = getattr(self, name)
            if not (0.0 <= v <= 1.0):
                raise ValidationError(f"{name} must be in [0, 1], got {v}")
        if self.width <= 0 or self.height <= 0:
            raise ValidationError(
                f"width/height must be > 0, got ({self.width}, {self.height})"
            )
        if self.shape == "polygon":
            if len(self.polygon) < 3:
                raise ValidationError("polygon crop needs at least 3 vertices")
            for x, y in self.polygon:
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    raise ValidationError(f"polygon vertices must be in [0, 1], got ({x}, {y})")


@dataclass(frozen=True, slots=True)
class JigsawParams:
    """Cut the relief plate into ``cols × rows`` interlocking jigsaw pieces on export."""

    enabled: bool = False
    cols: int = 4
    rows: int = 3
    seed: int = 0
    tab_size: float = 0.22  # tab depth as a fraction of the cell edge length
    jitter: float = 0.04  # random jitter of tab position/size (fraction of cell edge)
    kerf_mm: float = 0.2  # gap between pieces (each piece shrunk by kerf/2) for print fit
    min_piece_mm2: float = 1.0  # drop sliver pieces smaller than this (curved borders)

    def __post_init__(self) -> None:
        if self.cols < 1 or self.rows < 1:
            raise ValidationError(f"cols/rows must be >= 1, got ({self.cols}, {self.rows})")
        if not (0.0 < self.tab_size < 0.5):
            raise ValidationError(f"tab_size must be in (0, 0.5), got {self.tab_size}")
        if self.jitter < 0:
            raise ValidationError(f"jitter must be >= 0, got {self.jitter}")
        if self.kerf_mm < 0:
            raise ValidationError(f"kerf_mm must be >= 0, got {self.kerf_mm}")
        if self.min_piece_mm2 < 0:
            raise ValidationError(f"min_piece_mm2 must be >= 0, got {self.min_piece_mm2}")


@dataclass(frozen=True, slots=True)
class GeometryParams:
    """Physical dimensions of the printed relief plate (millimetres)."""

    footprint_mm: float = 200.0  # longest XY side of the plate; aspect ratio preserved
    relief_depth_mm: float = 6.0  # peak-to-valley relief amplitude
    base_thickness_mm: float = 2.0  # solid backing thickness below the deepest valley
    voxel_size_a: float | None = None  # override A/voxel; None => read from the MRC header

    def __post_init__(self) -> None:
        if self.footprint_mm <= 0:
            raise ValidationError(f"footprint_mm must be > 0, got {self.footprint_mm}")
        if self.relief_depth_mm < 0:
            raise ValidationError(f"relief_depth_mm must be >= 0, got {self.relief_depth_mm}")
        if self.base_thickness_mm <= 0:
            # base must be > 0 so wall faces are never degenerate and the solid stays manifold
            raise ValidationError(f"base_thickness_mm must be > 0, got {self.base_thickness_mm}")
        if self.voxel_size_a is not None and self.voxel_size_a <= 0:
            raise ValidationError(f"voxel_size_a must be > 0 or None, got {self.voxel_size_a}")


@dataclass(frozen=True, slots=True)
class MeshParams:
    """Mesh post-processing: smoothing, decimation, repair."""

    taubin_iterations: int = 0  # 0 disables smoothing (relief detail is usually wanted sharp)
    decimate_fraction: float | None = None  # keep-fraction in (0, 1]; None disables
    decimate_target_faces: int | None = None  # absolute target; overrides decimate_fraction
    backend: MeshBackend = "trimesh"
    repair: bool = True  # run the repair ladder after build / smooth / decimate

    def __post_init__(self) -> None:
        if self.taubin_iterations < 0:
            raise ValidationError(f"taubin_iterations must be >= 0, got {self.taubin_iterations}")
        if self.decimate_fraction is not None and not (0.0 < self.decimate_fraction <= 1.0):
            raise ValidationError(
                f"decimate_fraction must be in (0, 1] or None, got {self.decimate_fraction}"
            )
        if self.decimate_target_faces is not None and self.decimate_target_faces <= 0:
            raise ValidationError(
                f"decimate_target_faces must be > 0 or None, got {self.decimate_target_faces}"
            )
        if self.backend not in MESH_BACKENDS:
            raise ValidationError(f"backend must be one of {MESH_BACKENDS}, got {self.backend!r}")
