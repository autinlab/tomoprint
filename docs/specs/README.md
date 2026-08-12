# Specs

Use this directory for local execution artifacts related to the tomogram to printable plate pipeline.

## When To Create A Spec

Create a spec for work that changes:

- heightmap reduction or conditioning behavior
- plate meshing, cropping, or jigsaw cutting
- the export contract or mesh validity guarantees
- CLI or GUI surface that other work depends on

Small obvious fixes do not always need a spec folder.

## Naming

Use:

```text
docs/specs/<feature-slug>/
```

Use short kebab-case names.

## Files

- `feature.md`: local goal, constraints, success criteria, risks
- `plan.md`: implementation approach and validation path
- `tasks.md`: execution checklist

## Validation

Validation should emphasize watertightness, manifold geometry, and reproducibility of an exported plate from recorded parameters.

## Control Plane Relationship

RootRoute (`/home/qtallon/Documents/code/scripps-root-route`) owns priority and routing.
This repo owns the local execution artifacts.

If the work came from RootRoute, keep the local spec aligned with the matching item in its `STATE/now.md`.
