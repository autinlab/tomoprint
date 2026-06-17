"""Command-line interface for tomoprint (``tomoprint INPUT.mrc OUTPUT.stl [options]``)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from tomoprint.exceptions import TomoprintError
from tomoprint.io_mrc import load_volume, write_mesh
from tomoprint.params import (
    CropParams,
    FilterParams,
    GeometryParams,
    JigsawParams,
    MeshParams,
    ReduceParams,
)
from tomoprint.pipeline import run_pipeline, suggest_bin_factor


def convert(
    input: Annotated[Path, typer.Argument(help="Input .mrc tomogram", exists=True)],
    output: Annotated[Path, typer.Argument(help="Output mesh (.stl / .obj / .ply)")],
    # --- source ---
    mode: Annotated[str, typer.Option(help="slice | slab_mean | min | mean | max")] = "slice",
    index: Annotated[int, typer.Option(help="slice/slab centre; -1 = middle")] = -1,
    half_thickness: Annotated[int, typer.Option(help="+/- N slices for slab/projection")] = 0,
    axis: Annotated[int, typer.Option(help="collapse axis in (Z,Y,X); 0 = Z")] = 0,
    # --- contrast / conditioning ---
    sigma: Annotated[float, typer.Option(help="gaussian blur sigma (px); 0 = off")] = 1.0,
    bin: Annotated[int, typer.Option(help="integer downsample factor")] = 1,
    pclip_low: Annotated[float, typer.Option(help="low contrast percentile")] = 1.0,
    pclip_high: Annotated[float, typer.Option(help="high contrast percentile")] = 99.0,
    invert: Annotated[bool, typer.Option(help="flip craters <-> bumps")] = False,
    # --- geometry (mm) ---
    footprint: Annotated[float, typer.Option(help="longest plate side (mm)")] = 200.0,
    relief: Annotated[float, typer.Option(help="relief depth (mm)")] = 6.0,
    base: Annotated[float, typer.Option(help="solid base thickness (mm)")] = 2.0,
    voxel: Annotated[float | None, typer.Option(help="override A/voxel")] = None,
    # --- crop (rect/ellipse; polygon is GUI-only) ---
    crop_shape: Annotated[
        str | None, typer.Option(help="crop ROI shape: rect | ellipse (else no crop)")
    ] = None,
    crop_cx: Annotated[float, typer.Option(help="crop centre X (0..1 of width)")] = 0.5,
    crop_cy: Annotated[float, typer.Option(help="crop centre Y (0..1 of height)")] = 0.5,
    crop_w: Annotated[float, typer.Option(help="crop width (0..1 of footprint)")] = 1.0,
    crop_h: Annotated[float, typer.Option(help="crop height (0..1 of footprint)")] = 1.0,
    # --- jigsaw ---
    jigsaw: Annotated[bool, typer.Option(help="cut the plate into puzzle pieces")] = False,
    jigsaw_cols: Annotated[int, typer.Option(help="jigsaw columns")] = 4,
    jigsaw_rows: Annotated[int, typer.Option(help="jigsaw rows")] = 3,
    jigsaw_tab: Annotated[float, typer.Option(help="tab size (fraction of cell edge)")] = 0.22,
    jigsaw_kerf: Annotated[float, typer.Option(help="gap between pieces (mm)")] = 0.2,
    jigsaw_seed: Annotated[int, typer.Option(help="jigsaw randomization seed")] = 0,
    # --- mesh ---
    taubin: Annotated[int, typer.Option(help="Taubin smoothing iterations")] = 0,
    decimate: Annotated[float | None, typer.Option(help="keep-fraction 0..1")] = None,
    decimate_faces: Annotated[int | None, typer.Option(help="absolute target faces")] = None,
    repair: Annotated[bool, typer.Option(help="auto-repair to watertight")] = True,
    # --- other ---
    preview: Annotated[bool, typer.Option(help="fast: cap ~256px, skip smooth/decimate")] = False,
    format: Annotated[str | None, typer.Option(help="stl|obj|ply (else from extension)")] = None,
    report: Annotated[bool, typer.Option(help="print watertight diagnostics")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="progress logging")] = False,
) -> None:
    """Convert a cryo-ET tomogram into a watertight, 3D-printable relief plate."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        volume, header_voxel = load_volume(input)

        if preview:
            yx = tuple(s for i, s in enumerate(volume.shape) if i != axis)
            bin = max(bin, suggest_bin_factor(yx, max_dim=256))
            taubin, decimate, decimate_faces = 0, None, None
            typer.echo(f"[preview] heightmap {yx} -> bin {bin}, smoothing/decimation off")

        reduce_p = ReduceParams(mode=mode, index=index, half_thickness=half_thickness, axis=axis)
        filt_p = FilterParams(
            sigma=sigma, bin_factor=bin, pclip_low=pclip_low, pclip_high=pclip_high, invert=invert
        )
        geo_p = GeometryParams(
            footprint_mm=footprint, relief_depth_mm=relief, base_thickness_mm=base,
            voxel_size_a=voxel,
        )
        mesh_p = MeshParams(
            taubin_iterations=taubin, decimate_fraction=decimate,
            decimate_target_faces=decimate_faces, repair=repair,
        )
        crop_p = None
        if crop_shape is not None:
            crop_p = CropParams(
                enabled=True, shape=crop_shape, cx=crop_cx, cy=crop_cy,
                width=crop_w, height=crop_h,
            )
        jigsaw_p = JigsawParams(
            enabled=jigsaw, cols=jigsaw_cols, rows=jigsaw_rows,
            tab_size=jigsaw_tab, kerf_mm=jigsaw_kerf, seed=jigsaw_seed,
        )

        vox = voxel if voxel is not None else header_voxel

        def _progress(msg: str, frac: float) -> None:
            if verbose:
                typer.echo(f"  [{frac:5.0%}] {msg}")

        m, diag = run_pipeline(
            volume, vox, reduce_p, filt_p, geo_p, mesh_p,
            crop_p=crop_p, jigsaw_p=jigsaw_p, progress=_progress,
        )
        write_mesh(m, output, file_format=format)
    except TomoprintError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    ext = m.bounds[1] - m.bounds[0]
    typer.secho(
        f"wrote {output}  ({diag['n_faces']:,} faces, "
        f"{ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm, "
        f"watertight={diag['watertight']})",
        fg=typer.colors.GREEN,
    )
    if report:
        for key, val in diag.items():
            typer.echo(f"  {key}: {val}")


app = typer.Typer(
    add_completion=False,
    help="Convert cryo-ET tomograms into watertight, 3D-printable relief plates.",
)
app.command()(convert)


def main() -> None:
    """Console-script entry point (``tomoprint``)."""
    app()


if __name__ == "__main__":
    main()
