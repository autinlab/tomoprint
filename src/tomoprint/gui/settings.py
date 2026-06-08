"""Flat settings object bridging GUI widgets, JSON presets, and the core param dataclasses."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from tomoprint.params import FilterParams, GeometryParams, MeshParams, ReduceParams

SCHEMA_VERSION = 1


@dataclass
class ReliefSettings:
    """All tunable parameters in one flat object (the single source of truth for the GUI)."""

    # source
    mode: str = "slice"
    index: int = -1
    half_thickness: int = 0
    axis: int = 0
    bin_factor: int = 1
    # contrast
    sigma: float = 1.0
    pclip_low: float = 1.0
    pclip_high: float = 99.0
    invert: bool = False
    # relief geometry (mm)
    footprint_mm: float = 200.0
    relief_depth_mm: float = 6.0
    base_thickness_mm: float = 2.0
    # mesh post-processing
    taubin_iterations: int = 0
    decimate_percent: float = 0.0  # 0 = no decimation; otherwise % triangle reduction
    # reproducibility metadata (not applied to widgets)
    source_path: str | None = None
    source_dims: list[int] | None = None
    voxel_size_a: float | None = None

    def reduce_params(self) -> ReduceParams:
        return ReduceParams(
            mode=self.mode, index=self.index, half_thickness=self.half_thickness, axis=self.axis
        )

    def filter_params(self) -> FilterParams:
        return FilterParams(
            sigma=self.sigma, bin_factor=self.bin_factor,
            pclip_low=self.pclip_low, pclip_high=self.pclip_high, invert=self.invert,
        )

    def geometry_params(self) -> GeometryParams:
        return GeometryParams(
            footprint_mm=self.footprint_mm, relief_depth_mm=self.relief_depth_mm,
            base_thickness_mm=self.base_thickness_mm, voxel_size_a=self.voxel_size_a,
        )

    def mesh_params(self) -> MeshParams:
        if self.decimate_percent <= 0:
            frac = None
        else:
            frac = max(0.05, 1.0 - self.decimate_percent / 100.0)
        return MeshParams(taubin_iterations=self.taubin_iterations, decimate_fraction=frac)

    def to_json(self, path: str | Path) -> None:
        data = {"schema_version": SCHEMA_VERSION, **asdict(self)}
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def from_json(cls, path: str | Path) -> ReliefSettings:
        data = json.loads(Path(path).read_text())
        data.pop("schema_version", None)
        known = {f for f in cls.__dataclass_fields__}  # ignore unknown keys gracefully
        return cls(**{k: v for k, v in data.items() if k in known})
