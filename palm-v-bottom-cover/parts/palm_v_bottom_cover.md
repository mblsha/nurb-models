# Palm V aluminium bottom cover

```toml
target = { file = "scans/palm-v-bottom-cover-comparison-triangles.ply.gz", units = "mm", tolerance_mm = 0.35, transform = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0] }

[part]
min_wall = 0.55
```

## Intended part

A smooth bent aluminium sheet with the full rising perimeter, deep notched end, nominally planar broad field, localized central stamp, centered rectangular through-slot, and offset Reset hole. The entire formed right half is offset along its normals toward the observed interior, then mirrored and united. The Reset hole is the only intended asymmetry. The model has no invented horizontal inward flange and no filled ellipsoid behind the stamp.

## Observed and nominal shape

The reference retains the original aligned scan triangles. The editable surface uses a robust symmetric fit to the exterior and side-return observations from all three groups. A dedicated surface parameterization resolves the nearly vertical rims without flattening them into a height map. The source scans remain unaltered.

`straight_rims=True` makes the marked rim crests and adjacent bend profiles straight along their physical runs, at constant Z in the part frame. The complete curved cross-section is retained and repeated along each fitted axis; this is not a straight UV trim over a wavy surface. Side runs retain their small measured taper and are exactly mirrored. The split returns retain their measured angle in plan view. Rounded corner transitions lie outside the straight core runs. The lower long-side transition uses a smooth quintic blend into the straight run, removing a sub-gauge curvature spike in the former fit. At the opposite, continuous end, a symmetric local pole correction preserves the upturned lip and straight crest while broadening the root and fairing its transition into the long sides. The corrected back is the rear-seat master for the plastic body, so rebuild the body after regenerating this fit. Set `straight_rims=False` to restore the earlier unconstrained rim fit.

`level_inner_rims=True` also levels the normal-offset inside free edges along those straight core runs while retaining the 0.65 mm normal sheet gauge and the curved corner transitions. The reopened STEP spans at most 0.00634 mm along each long-side core, 0.00877 mm along the continuous end, and 0.00461 mm along the split-end cores. `references/inner-rim-fit.json` stores the symmetric local bend-band correction, and `python references/level_inner_rims.py` regenerates it after a rim fit change. The full long edges intentionally rise through their end transitions and are not horizontal there.

| Core run | Nominal plan line, mm | Level Z, mm | Core extent |
|---|---|---:|---|
| Continuous end | Y = 55.73 | 3.12 | X = −28 to +28 mm |
| Mirrored long sides | abs(X) = 38.54173 + 0.00601854 Y | 1.30 | Y = −28 to +40 mm |
| Split end returns | Y = −61.42917 + 0.21745228 abs(X) | 4.646 | abs(X) = 18 to 36 mm |

These are nominal line constraints inferred from the aligned scan, not factory drawing dimensions. `references/straight-rim-fit.json` records the targets, complete averaged bend profiles, symmetric surface coefficients, source-fit hash, and fitting residuals. Regenerate it after refitting the scan with `python references/straighten_rims.py` before rebuilding the part.

The nominal split-end trim now keeps each long side at Z≈1.30 mm through Y≈−47 mm, then turns into the level Z≈4.646 mm wing crest near Y≈−53 mm. The outer walls of the central split are vertical and mirrored; the inner offset walls retain the normal 0.65 mm sheet gauge. At +Y, the hem and rounded corner trim descend monotonically from the level center run while the broad panel stays in its nominal plane away from the compact edge bend. The flat-then-compact split-end turn is an intentional design inference: the observed scan has a longer gradual rise, so local scan deviation there is expected and is not evidence of a better observation fit. `smooth_split_end=False` is used internally by the plastic seat master to keep that contact numerically stable; the exposed aluminium uses the smooth default.

The continuous-end curvature correction of the preceding fitted surface was a nominal design choice. The three observed scan groups disagree at the bend root by several tenths of a millimetre, and the former exterior radius fell to about 0.53 mm, below the 0.65 mm sheet gauge. Before the planar-field correction, the fixed analytic sampling grid measured a 0.956 mm exterior minimum principal radius at the root and 0.830 mm across the adjacent side transition, with no sampled sub-gauge radii. These historical fit numbers are not a curvature certification of the present STEP; rerun a trim-aware STEP curvature audit after any surface change. The scan-to-CAD exterior-root p95 rises from 0.240 mm in the project baseline to 0.282 mm in the V4 trial and 0.346 mm in the final fit; preserving a feasible, smooth nominal sheet takes priority over that sparse local scan trace. Run `python references/audit_far_end_curvature.py` to reproduce the curvature numbers in `build/far-end-curvature-audit.json`. The quoted local scan p95 series is reproduced by `python references/audit_far_end_scan_fit.py` from the archived trial STEPs and unchanged comparison PLY; see `build/analysis/far-end-trials/robust-fit.json` and its manifest.

`longitudinal_straightening=1.0` is the default intended manufactured shape. It removes the coherent approximately 0.31 mm lengthwise bow measured on broad side stripes, anchored at Y=-40 and Y=48 mm. The current nominal reconstruction additionally replaces the scan-derived broad transverse crown with a true plane while preserving the local stamp and perimeter rise. Set `longitudinal_straightening=0.0` and `straight_rims=False` to recover the observed-fit baseline. This correction is an explicit nominal-design inference requested by the owner, not proof of the original factory design.

The sheet gauge is provisionally 0.65 mm, supported by same-group paired exterior/interior scan patches. Direct micrometer measurements remain desirable. The slot is provisionally 7.2 by 2.7 mm at Y=15.3 mm; the Reset hole is 1.8 mm at X=12.8, Y=19.16 mm. Cut-edge dimensions and group residual registration remain uncertain at approximately a few tenths of a millimetre.

Glue, clamps, fixtures, scan noise and accidental asymmetric dents are excluded. The two small lower corner dots visible in photos are not individually reconstructed: their exact formed profile is unresolved in this smooth model.

## Nominal planar field

The broad exterior sheet is now exactly planar at Z = -0.30 mm, apart from the localized formed feature around the centered slot and Reset opening, the compact -Y split return, and the perimeter bends. The datum is the approximate median height of the prior broad-field fit outside the formed regions. A smooth separable blend retains signed local stamp relief over approximately abs(X) ≤ 26 mm and Y = 9 to 30 mm; the actual B-spline influence tapers outside those control-pole bounds. The ±X corner adjustments at the +Y edge are mirror-paired and no more than 0.005 mm at any pole to preserve the plastic mating seat. This planarization is a manufacturing-intent inference requested by the owner: the scanned sheet has a shallow transverse crown and local warping, so local scan deviation is expected. The body must be rebuilt from this sheet and the reopened STEP contact and co-occupancy checks rerun before claiming fit. Set `straight_rims=False` to inspect the earlier scan-derived broad surface without this nominal planarization. Run `python references/audit_rear_planarity.py` to sample the reopened STEP broad field and mirrored surface; its report is `build/analysis/planar-field/exact-plane-report.json`.

## Validation and exports

Run `python references/export_checked.py`, then `python references/validate_reconstruction.py` in a Python environment containing NURB and its dependencies. The export script tessellates the reopened STEP with build123d's relative linear mesher setting of 0.0024 and angular setting of 0.025 radians. It preserves the complete physical mesh without welding or seam repairs, removing only detached numerical artifacts with extent below 0.1 mm, area below 10⁻⁷ mm², and local and bounding-box volumes below 10⁻¹⁰ mm³, or exactly zero area. Each removed component and the final file hashes are recorded in `build/export-validation.json`.

The independent reopened-artifact validator checks normal gauge, mirrored surfaces, the through-slot and Reset exception, single-solid STEP topology, straightness and level of all five reopened physical rim runs within 0.01 mm, whole-file STL/3MF watertightness, and adaptive STEP volume against mesh volume. `build/reconstruction_validation.json` records the evidence. Generic print overhang checks do not establish whether this formed aluminium part matches its manufactured counterpart. Physical fit remains unverified.

The CAD kernel's default volume integration can be inaccurate on offset spline surfaces; use the adaptive per-knot STEP integration in the validation report rather than an unqualified generic card volume.

## Provenance

`references/surface-fit.json` records the frozen source archive hash, exterior-fit coefficients, masks, residuals and longitudinal bow estimate. Recreate it with `python references/fit_surface.py --archive /path/to/project.zip`. `references/import_observed_mesh.py` supplies the checked original THREE hierarchy and source PLY reader. `references/rejected-v1/` preserves the earlier rejected reconstruction.
