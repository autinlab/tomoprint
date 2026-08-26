# AGENTS

## Purpose

This repo turns cryo-ET tomograms into clean, watertight, 3D-printable relief plates, through a scriptable library, a CLI, and a desktop GUI.

## In Scope

- tomogram to heightmap reduction: single slice, slab, and min / mean / max projection
- heightmap conditioning: denoise, contrast, optional invert
- watertight plate meshing: relief top surface, flat base, side walls
- region-of-interest crops: rectangle, ellipse, freehand polygon
- interlocking jigsaw cutting on export
- STL / OBJ / PLY export, the CLI, and the PySide6 GUI

## Out Of Scope

- segmentation and morphometrics, which belong in `sam-capsids` and `capsid-morphometrics`
- tomogram acquisition and reconstruction, which belong in `deep-parakeet`

## Local Constraints

- exported meshes must stay manifold and watertight — that is the product, not a nice-to-have
- keep the pure-core library importable without the VTK / Qt stack
- record the parameters that produced any exported mesh
- prefer the library and CLI path over GUI-only behavior

## Spec Location

Local specs live in `docs/specs/`.

## Standard Workflow

1. Create `docs/specs/<feature-slug>/feature.md`.
2. Write the implementation approach in `plan.md`.
3. Break execution into `tasks.md`.
4. Implement in the repo.
5. Validate with tests, mesh validity checks, or inspection of an exported plate.

## Definition Of Done

Work is done when:

- the pipeline or export change is implemented
- exported meshes are still manifold and watertight
- the parameters that produced the mesh are recorded
