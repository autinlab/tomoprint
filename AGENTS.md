# AGENTS

## Purpose

This repo turns cryo-ET tomograms into clean, watertight, 3D-printable relief plates, through a scriptable library, a CLI, and a desktop GUI.

## Control plane

Planning for this work lives in RootRoute at `/home/qtallon/Documents/code/scripps-root-route`.

- Start from an item in that repo's `STATE/now.md`, or from a local need — and if it is a
  local need, say so there.
- Local rules win here. That repo decides what to work on and what must not happen;
  this repo decides how it gets done.
- When you finish, or get blocked, or learn something that changes the plan, write it back
  into that item. Nothing else needs to go back.
- Do not copy plans, priorities, or decisions into this repo. Point at them.

Installed: 2026-08-12

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
- control-plane planning, which lives in RootRoute

## Local Constraints

- exported meshes must stay manifold and watertight — that is the product, not a nice-to-have
- keep the pure-core library importable without the VTK / Qt stack
- record the parameters that produced any exported mesh
- prefer the library and CLI path over GUI-only behavior

## Spec Location

Local specs live in `docs/specs/`.

## Standard Workflow

1. Start from an item in RootRoute's `STATE/now.md`, or from a repo-local need.
2. Create `docs/specs/<feature-slug>/feature.md`.
3. Write the implementation approach in `plan.md`.
4. Break execution into `tasks.md`.
5. Implement in the repo.
6. Validate with tests, mesh validity checks, or inspection of an exported plate.
7. Write meaningful status changes back into the RootRoute item.

## Definition Of Done

Work is done when:

- the pipeline or export change is implemented
- exported meshes are still manifold and watertight
- the parameters that produced the mesh are recorded
- the RootRoute item has been updated if the status, blocker, or outcome changed

## Reporting Back

Write back to the RootRoute item only at meaningful checkpoints:

- status changed → the item's `Status:`
- blocker appeared or cleared → the item's `Status:` and `Next action`
- branch / PR exists → the item's `Handoff:`
- the export contract or mesh validity guarantee changed → the item's `Next action`

Any of these advances the item's `Updated:`.
