# Palm V aluminium bottom cover

```toml
target = { file = "scans/palm-v-bottom-cover-comparison-triangles.ply.gz", units = "mm", tolerance_mm = 0.35, transform = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0] }

[part]
min_wall = 0.55
```

## Intended part

A smooth bent aluminium sheet with the full rising perimeter, deep notched end, transverse crown, central stamp, centered rectangular through-slot, and offset Reset hole. The entire formed right half is offset along its normals toward the observed interior, then mirrored and united. The Reset hole is the only intended asymmetry. The model has no invented horizontal inward flange and no filled ellipsoid behind the stamp.

## Observed and nominal shape

The reference retains the original aligned scan triangles. The editable surface uses a robust symmetric fit to the exterior and side-return observations from all three groups. A dedicated surface parameterization resolves the nearly vertical rims without flattening them into a height map. The source scans remain unaltered.

`longitudinal_straightening=1.0` is the default intended manufactured shape. It removes the coherent approximately 0.31 mm lengthwise bow measured on broad side stripes, anchored at Y=-40 and Y=48 mm. It preserves the intentional transverse crown, local stamp, and rim rise relative to the adjacent skin. Set the parameter to `0.0` to recover the observed-fit baseline. This correction is an explicit nominal-design inference requested by the owner, not proof of the original factory design.

The sheet gauge is provisionally 0.65 mm, supported by same-group paired exterior/interior scan patches. Direct micrometer measurements remain desirable. The slot is provisionally 7.2 by 2.7 mm at Y=15.3 mm; the Reset hole is 1.8 mm at X=12.8, Y=19.16 mm. Cut-edge dimensions and group residual registration remain uncertain at approximately a few tenths of a millimetre.

Glue, clamps, fixtures, scan noise and accidental asymmetric dents are excluded. The two small lower corner dots visible in photos are not individually reconstructed: their exact formed profile is unresolved in this smooth model.

## Validation and exports

Run `python references/export_checked.py`, then `python references/validate_reconstruction.py` in a Python environment containing NURB and its dependencies. The export script preserves one complete physical mesh, removing only verified negligible tessellation components and repairing strictly bounded submicron nonmanifold edges. Every repair and the final file hashes are recorded in `build/export-validation.json`.

The independent reopened-artifact validator checks normal gauge, mirrored surfaces, the through-slot and Reset exception, single-solid STEP topology, whole-file STL/3MF watertightness, and adaptive STEP volume against mesh volume. `build/reconstruction_validation.json` records the evidence. Generic print overhang checks do not establish whether this formed aluminium part matches its manufactured counterpart. Physical fit remains unverified.

The CAD kernel's default volume integration can be inaccurate on offset spline surfaces; use the adaptive per-knot STEP integration in the validation report rather than an unqualified generic card volume.

## Provenance

`references/surface-fit.json` records the frozen source archive hash, exterior-fit coefficients, masks, residuals and longitudinal bow estimate. Recreate it with `python references/fit_surface.py --archive /path/to/project.zip`. `references/import_observed_mesh.py` supplies the checked original THREE hierarchy and source PLY reader. `references/rejected-v1/` preserves the earlier rejected reconstruction.
