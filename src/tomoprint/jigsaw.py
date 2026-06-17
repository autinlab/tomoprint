"""Cut a relief-plate solid into interlocking jigsaw pieces.

The footprint outline (a rectangle for a plain plate, or the crop outline for a shaped plate) is
partitioned into a ``cols x rows`` grid. Each internal grid edge gets a classic mushroom *tab*
(a narrow neck + a wider bulb, so the bulb overhangs the neck and the pieces actually lock). The
tab is built as a shapely shape, *added* to one piece and *subtracted* from its neighbour, so the
pieces always tile the outline exactly with valid geometry — no fragile hand-sampled curves.

Each piece polygon is then extruded to a prism and boolean-intersected with the relief solid
(``manifold`` engine), giving one watertight body per piece. Pure shapely/trimesh — no Qt/VTK.
"""

from __future__ import annotations

import numpy as np

from tomoprint.params import JigsawParams

# margin (mm) added above/below the plate when extruding piece prisms for the boolean cut
_Z_MARGIN = 1.0


def _tab_shape(mid, normal, edge_len: float, params: JigsawParams, rng: np.random.Generator):
    """A mushroom tab (neck + overhanging bulb) straddling an internal edge.

    ``mid`` is the (jittered) edge midpoint, ``normal`` the unit direction the tab protrudes into
    the neighbouring cell. Returns a shapely polygon. The bulb is wider than the neck so assembled
    pieces interlock instead of merely registering.
    """
    from shapely.affinity import rotate, translate
    from shapely.geometry import Point, box

    scale = params.tab_size * edge_len
    bulb_r = 0.5 * scale
    neck_w = 0.6 * bulb_r  # neck narrower than the bulb diameter => overhang/locking
    bulb_off = 1.2 * bulb_r  # bulb centre sits past the neck, inside the neighbour

    # build pointing along +y, edge along x at the origin, then rotate/translate into place
    neck = box(-neck_w / 2.0, -0.3 * bulb_r, neck_w / 2.0, bulb_off)
    bulb = Point(0.0, bulb_off).buffer(bulb_r, quad_segs=24)
    tab = neck.union(bulb)

    angle = np.degrees(np.arctan2(normal[1], normal[0])) - 90.0  # +y -> normal
    tab = rotate(tab, angle, origin=(0, 0), use_radians=False)
    return translate(tab, xoff=float(mid[0]), yoff=float(mid[1]))


def _largest(geom):
    """Return the largest polygon of a (possibly Multi)Polygon, or the polygon itself."""
    if geom.geom_type == "MultiPolygon":
        return max(geom.geoms, key=lambda g: g.area)
    return geom


def piece_polygons(outline, params: JigsawParams) -> list:
    """Partition ``outline`` (a shapely Polygon) into ``cols*rows`` interlocking piece polygons.

    Pieces are shrunk by ``kerf_mm/2`` (print-fit clearance) and slivers below ``min_piece_mm2``
    are dropped. For a shaped outline the border pieces follow the outline.
    """
    from shapely.geometry import box

    rng = np.random.default_rng(params.seed)
    x0, y0, x1, y1 = outline.bounds
    cols, rows = params.cols, params.rows
    cw = (x1 - x0) / cols
    ch = (y1 - y0) / rows

    # base rectangular cells, indexed [row][col]
    cells = [
        [
            box(x0 + c * cw, y0 + r * ch, x0 + (c + 1) * cw, y0 + (r + 1) * ch)
            for c in range(cols)
        ]
        for r in range(rows)
    ]

    def jit(amount: float) -> float:
        return float(rng.uniform(-params.jitter, params.jitter)) * amount

    # vertical internal edges: between (r, c) and (r, c+1)
    for r in range(rows):
        for c in range(cols - 1):
            ex = x0 + (c + 1) * cw
            my = y0 + (r + 0.5) * ch + jit(ch)
            normal = np.array([1.0, 0.0]) if rng.random() < 0.5 else np.array([-1.0, 0.0])
            tab = _tab_shape((ex, my), normal, ch, params, rng)
            if normal[0] > 0:  # tab grows from left cell into right cell
                src, tgt = (r, c), (r, c + 1)
            else:
                src, tgt = (r, c + 1), (r, c)
            cells[src[0]][src[1]] = _largest(cells[src[0]][src[1]].union(tab))
            cells[tgt[0]][tgt[1]] = _largest(cells[tgt[0]][tgt[1]].difference(tab))

    # horizontal internal edges: between (r, c) and (r+1, c)
    for r in range(rows - 1):
        for c in range(cols):
            ey = y0 + (r + 1) * ch
            mx = x0 + (c + 0.5) * cw + jit(cw)
            normal = np.array([0.0, 1.0]) if rng.random() < 0.5 else np.array([0.0, -1.0])
            tab = _tab_shape((mx, ey), normal, cw, params, rng)
            if normal[1] > 0:  # tab grows from lower cell into upper cell
                src, tgt = (r, c), (r + 1, c)
            else:
                src, tgt = (r + 1, c), (r, c)
            cells[src[0]][src[1]] = _largest(cells[src[0]][src[1]].union(tab))
            cells[tgt[0]][tgt[1]] = _largest(cells[tgt[0]][tgt[1]].difference(tab))

    pieces = []
    for row in cells:
        for poly in row:
            clipped = _largest(poly.intersection(outline))
            if params.kerf_mm > 0:
                clipped = _largest(clipped.buffer(-params.kerf_mm / 2.0))
            if clipped.is_empty or clipped.area < params.min_piece_mm2:
                continue
            if not clipped.is_valid:
                clipped = _largest(clipped.buffer(0))
            pieces.append(clipped)
    return pieces


def cut_mesh_into_pieces(relief_mesh, polys: list, z_lo: float, z_hi: float) -> list:
    """Intersect ``relief_mesh`` with each piece polygon's prism. One watertight body per piece."""
    import trimesh

    height = (z_hi - z_lo) + 2.0 * _Z_MARGIN
    pieces = []
    for poly in polys:
        prism = trimesh.creation.extrude_polygon(poly, height=height)
        prism.apply_translation((0.0, 0.0, z_lo - _Z_MARGIN))
        cut = trimesh.boolean.intersection([relief_mesh, prism], engine="manifold")
        if cut.is_empty or len(cut.faces) == 0:
            continue
        # a boolean may return a scene/concatenation; split into watertight bodies
        for body in cut.split(only_watertight=False) or [cut]:
            if len(body.faces):
                pieces.append(body)
    return pieces
