"""Build a watertight, manifold relief-plate solid from a heightmap, plus smooth/decimate/verify.

The solid (``build_relief_mesh``) is a relief top surface + a flat bottom at ``z=0`` + four
vertical side walls (the "Variant A" full-mirrored-grid construction). Everything is built as
vectorized numpy vertex/face arrays handed to :class:`trimesh.Trimesh` — no VTK in this layer.
"""

from __future__ import annotations

import logging

import numpy as np

from tomoprint.exceptions import NonManifoldError, ValidationError
from tomoprint.heightmap import Heightmap

logger = logging.getLogger("tomoprint")


def _wall_faces(a_top, b_top, a_bot, b_bot, vertices, outward) -> np.ndarray:
    """Two outward-facing triangles per wall quad (corners a_top, b_top, b_bot, a_bot).

    A wall is planar (constant x or y), so both triangles share one normal direction. We orient
    the whole wall analytically against the known ``outward`` vector — O(1) per wall — which keeps
    the solid consistently wound without trimesh's slow global ``fix_winding``.
    """
    tri1 = np.column_stack([a_top, b_top, b_bot])
    tri2 = np.column_stack([a_top, b_bot, a_bot])
    p0, p1, p2 = vertices[tri1[0, 0]], vertices[tri1[0, 1]], vertices[tri1[0, 2]]
    if np.dot(np.cross(p1 - p0, p2 - p0), outward) < 0:
        tri1 = tri1[:, ::-1]
        tri2 = tri2[:, ::-1]
    faces = np.empty((2 * a_top.size, 3), dtype=np.int64)
    faces[0::2] = tri1
    faces[1::2] = tri2
    return faces


def build_relief_mesh(hm: Heightmap):
    """Turn a :class:`Heightmap` into a closed, watertight, outward-oriented solid.

    Returns a :class:`trimesh.Trimesh`. Faces are wound outward by construction (no slow global
    repair), so the result is consistently oriented and printable as-is.
    """
    import trimesh

    z = np.ascontiguousarray(hm.z, dtype=np.float64)
    h, w = z.shape
    if h < 2 or w < 2:
        raise ValidationError(f"heightmap too small to mesh: {z.shape}")
    if hm.dx_mm <= 0 or hm.dy_mm <= 0:
        raise ValidationError(f"pixel pitch must be > 0, got dx={hm.dx_mm}, dy={hm.dy_mm}")

    n_grid = h * w  # offset O between the top block and the mirrored bottom block

    # --- vertices: top grid at z, mirrored bottom grid at z=0 -----------------------------
    xs = np.arange(w, dtype=np.float64) * hm.dx_mm
    ys = np.arange(h, dtype=np.float64) * hm.dy_mm
    xx, yy = np.meshgrid(xs, ys)  # (h, w)
    xr, yr = xx.ravel(), yy.ravel()
    top = np.column_stack([xr, yr, z.ravel()])
    bottom = np.column_stack([xr, yr, np.zeros(n_grid)])
    vertices = np.vstack([top, bottom])

    # --- top & bottom faces (vectorized over grid quads) ----------------------------------
    rr, cc = np.meshgrid(np.arange(h - 1), np.arange(w - 1), indexing="ij")
    tv00 = (rr * w + cc).ravel()
    tv01 = tv00 + 1
    tv10 = tv00 + w
    tv11 = tv00 + w + 1
    n_quad = tv00.size

    top_faces = np.empty((2 * n_quad, 3), dtype=np.int64)
    top_faces[0::2] = np.column_stack([tv00, tv01, tv11])  # CCW from above -> +Z
    top_faces[1::2] = np.column_stack([tv00, tv11, tv10])

    bv00, bv01, bv10, bv11 = (tv00 + n_grid, tv01 + n_grid, tv10 + n_grid, tv11 + n_grid)
    bottom_faces = np.empty((2 * n_quad, 3), dtype=np.int64)
    bottom_faces[0::2] = np.column_stack([bv00, bv11, bv01])  # reversed -> -Z
    bottom_faces[1::2] = np.column_stack([bv00, bv10, bv11])

    # --- four side walls stitching top perimeter to bottom perimeter ----------------------
    # Each wall is planar with a known outward direction; combined with top (+Z) and bottom (-Z)
    # the whole solid is consistently outward-oriented by construction.
    ci = np.arange(w - 1)
    ri = np.arange(h - 1)
    south_base = (h - 1) * w
    walls = np.vstack(
        [
            _wall_faces(ci, ci + 1, ci + n_grid, ci + 1 + n_grid, vertices, (0.0, -1.0, 0.0)),
            _wall_faces(
                south_base + ci, south_base + ci + 1,
                south_base + ci + n_grid, south_base + ci + 1 + n_grid,
                vertices, (0.0, 1.0, 0.0),
            ),
            _wall_faces(
                ri * w, (ri + 1) * w, ri * w + n_grid, (ri + 1) * w + n_grid,
                vertices, (-1.0, 0.0, 0.0),
            ),
            _wall_faces(
                ri * w + (w - 1), (ri + 1) * w + (w - 1),
                ri * w + (w - 1) + n_grid, (ri + 1) * w + (w - 1) + n_grid,
                vertices, (1.0, 0.0, 0.0),
            ),
        ]
    )

    faces = np.vstack([top_faces, bottom_faces, walls])
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def smooth_mesh(mesh, iterations: int, lamb: float = 0.5, nu: float = -0.53):
    """Taubin (lambda/nu) smoothing. ``iterations <= 0`` is a no-op. Preserves topology."""
    if iterations <= 0:
        return mesh
    import trimesh

    out = mesh.copy()
    trimesh.smoothing.filter_taubin(out, lamb=lamb, nu=nu, iterations=int(iterations))
    return out


def decimate_mesh(mesh, fraction: float | None, target_faces: int | None):
    """Quadric decimation to a keep-fraction or absolute face target. No-op when both are None.

    Prefers the ``fast_simplification`` backend; falls back to trimesh's built-in decimator.
    """
    if fraction is None and target_faces is None:
        return mesh
    import trimesh

    n = len(mesh.faces)
    if target_faces is not None:
        reduction = 1.0 - min(1.0, target_faces / max(1, n))
    else:
        reduction = 1.0 - float(fraction)
    if reduction <= 0:
        return mesh

    try:
        import fast_simplification

        v, f = fast_simplification.simplify(
            np.asarray(mesh.vertices), np.asarray(mesh.faces), target_reduction=reduction
        )
        return trimesh.Trimesh(vertices=v, faces=f, process=False)
    except ImportError:
        tgt = target_faces if target_faces is not None else max(4, int(n * fraction))
        return mesh.simplify_quadric_decimation(face_count=tgt)


def verify_watertight(mesh) -> dict:
    """Return a diagnostics dict describing the mesh's manifold/printability status."""
    try:
        volume = float(mesh.volume)
    except Exception:  # pragma: no cover - volume is robust for our solids
        volume = float("nan")
    return {
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "euler_number": int(mesh.euler_number),
        "volume_mm3": volume,
        "n_faces": int(len(mesh.faces)),
        "n_vertices": int(len(mesh.vertices)),
    }


def repair_mesh(mesh):
    """Repair ladder: merge -> drop degenerate/duplicate -> fix winding/normals -> fill holes.

    Idempotent and safe to run after decimation (which can introduce small artifacts).
    """
    import trimesh

    m = mesh.copy()
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.update_faces(m.unique_faces())
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_winding(m)
    trimesh.repair.fix_normals(m)
    if not m.is_watertight:
        trimesh.repair.fill_holes(m)
        trimesh.repair.fix_normals(m)
    trimesh.repair.fix_inversion(m)
    return m


def ensure_watertight(mesh, *, repair: bool = True):
    """Verify the mesh; if not watertight and ``repair`` is set, run the ladder once and re-verify.

    Raises :class:`NonManifoldError` (with diagnostics) if the result is still not watertight.
    """
    diag = verify_watertight(mesh)
    if diag["watertight"] and diag["winding_consistent"]:
        return mesh, diag
    if not repair:
        raise NonManifoldError("mesh is not watertight and repair is disabled", diag)
    logger.info("mesh not watertight (%s); running repair ladder", diag)
    mesh = repair_mesh(mesh)
    diag = verify_watertight(mesh)
    if not diag["watertight"]:
        raise NonManifoldError("mesh is still not watertight after repair", diag)
    return mesh, diag
