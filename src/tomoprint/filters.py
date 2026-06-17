"""2D heightmap conditioning: denoise, downsample (bin), contrast-normalize, invert."""

from __future__ import annotations

import numpy as np


def gaussian_smooth(hm: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian-blur the 2D heightmap (sigma in pixels). ``sigma <= 0`` is a no-op."""
    if sigma <= 0:
        return hm
    from scipy.ndimage import gaussian_filter

    return gaussian_filter(hm.astype(np.float32, copy=False), sigma=float(sigma))


def downsample_heightmap(hm: np.ndarray, bin_factor: int) -> np.ndarray:
    """Integer block-mean downsample. ``bin_factor <= 1`` is a no-op.

    The array is cropped to a multiple of ``bin_factor`` before reducing so the binning never
    introduces zero-padded edge artifacts.
    """
    if bin_factor <= 1:
        return hm
    from skimage.measure import block_reduce

    h, w = hm.shape
    hc, wc = h - (h % bin_factor), w - (w % bin_factor)
    if hc < bin_factor or wc < bin_factor:
        return hm  # too small to bin; leave unchanged
    cropped = hm[:hc, :wc]
    reduced = block_reduce(cropped, block_size=(bin_factor, bin_factor), func=np.mean)
    return np.ascontiguousarray(reduced, dtype=np.float32)


def normalize_contrast(
    hm: np.ndarray, p_low: float, p_high: float, mask: np.ndarray | None = None
) -> np.ndarray:
    """Percentile-clip to ``[p_low, p_high]`` then rescale to float32 ``[0, 1]``.

    Robust to NaNs/infs and to flat input (returns zeros when the percentile range collapses).
    When ``mask`` is given (a boolean array shaped like ``hm``), the clip percentiles are computed
    over the in-mask pixels only, so contrast adapts to a cropped shape rather than the full box.
    """
    src = hm[mask] if mask is not None else hm
    finite = src[np.isfinite(src)]
    if finite.size == 0:
        return np.zeros_like(hm, dtype=np.float32)
    lo = float(np.percentile(finite, p_low))
    hi = float(np.percentile(finite, p_high))
    if hi <= lo:
        return np.zeros_like(hm, dtype=np.float32)
    out = (hm.astype(np.float32, copy=False) - lo) / (hi - lo)
    out = np.clip(out, 0.0, 1.0)
    return np.nan_to_num(out, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)


def apply_invert(hm01: np.ndarray, invert: bool) -> np.ndarray:
    """Return ``1 - hm01`` if ``invert`` else ``hm01``. Expects a 0..1 array."""
    if not invert:
        return hm01
    return (1.0 - hm01).astype(np.float32)
