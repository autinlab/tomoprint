"""Collapse a 3D volume (Z, Y, X) into a 2D heightmap via slice / slab / projection."""

from __future__ import annotations

import numpy as np

from tomoprint.params import ReduceParams


def resolve_slice_index(n: int, index: int) -> int:
    """Resolve a (possibly negative) slice index into a valid ``[0, n-1]`` value.

    A negative index selects the middle slice (``n // 2``); otherwise the index is clamped
    into range.
    """
    if n <= 0:
        raise ValueError(f"axis length must be positive, got {n}")
    if index < 0:
        return n // 2
    return min(index, n - 1)


def reduce_to_heightmap(volume: np.ndarray, params: ReduceParams) -> np.ndarray:
    """Reduce ``volume`` (Z, Y, X) to a 2D float32 heightmap along ``params.axis``.

    With the default ``axis=0`` the result is ``(Y, X)``. ``mode="slice"`` returns a single
    slice (ignoring ``half_thickness``); the other modes operate on the slab
    ``[index - N, index + N]`` clamped to the array bounds.
    """
    if volume.ndim != 3:
        raise ValueError(f"reduce_to_heightmap expects a 3D array, got {volume.ndim}D")

    axis = params.axis
    n = volume.shape[axis]
    center = resolve_slice_index(n, params.index)

    if params.mode == "slice":
        plane = np.take(volume, center, axis=axis)
        return np.ascontiguousarray(plane, dtype=np.float32)

    lo = max(0, center - params.half_thickness)
    hi = min(n - 1, center + params.half_thickness)
    slab = np.take(volume, np.arange(lo, hi + 1), axis=axis)

    if params.mode in ("mean", "slab_mean"):
        plane = slab.mean(axis=axis)
    elif params.mode == "min":
        plane = slab.min(axis=axis)
    elif params.mode == "max":
        plane = slab.max(axis=axis)
    else:  # pragma: no cover - guarded by ReduceParams validation
        raise ValueError(f"unknown reduction mode {params.mode!r}")

    return np.ascontiguousarray(plane, dtype=np.float32)
