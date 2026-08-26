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

If the work came from `scripps-rr`, that repo owns priority and routing and this repo
owns the local execution artifacts. If it is a local need, this file is the whole contract.

Keep the local spec aligned with the matching item in that repo's `STATE/now.md`.
