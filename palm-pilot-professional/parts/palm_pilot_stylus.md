# Palm Pilot Professional stylus

```toml
target = { file = "scans/stylus-without-blu-tack-corrected.glb", units = "mm", tolerance_mm = 0.25, transform = [0.14154864921279275, -0.79403379359508, 0.5911635260526816, 1.1218836325040487, -0.040100753363271444, 0.5920868946582, 0.8048757908855921, -1.9823030947793658, -0.9891187539854513, -0.13763518373953432, 0.05196774683640626, 52.988595534522624, 0.0, 0.0, 0.0, 1.0] }
```

## What it is

An editable reconstruction of the original textured stylus scan, with a circular shaft, rounded writing tip, solid extraction rib, rounded head and eight measured molded grooves. The original textured PLY and PNG are included unchanged; the upload archive remains in the local development archive. The isolated palm_pilot_stylus view exposes this part separately from the Pilot.

## Measured construction

The fitted straight shaft diameter is 5.180704 mm and the observed tip-to-head span is 107.368 mm. The shaft fit used 6,589 unobscured vertices, with median radial residual 0.0211 mm and 95th percentile 0.0516 mm. Units are provisionally millimetres. The cylindrical shaft reconstructs the interval hidden by Blu Tack; it does not claim to recover unseen OEM geometry.

The writing tip now follows measured radial sections through a 15.0 mm taper and smooth shaft join. Its rounded nose has radius approximately 0.387 mm at Z0.10 and 0.602 mm at Z0.25. A shape-preserving piecewise cubic meridian is revolved around the shaft axis. This retains circular sections and prevents interpolation from doubling back along Z. The public tip_length default is 15.0 mm.

The upper protrusion is a solid extraction rib. Original scan surfaces and a contemporary Pilot stylus account support the continuous web. The previous open cantilever slot and rectangular bridge were unsupported and have been removed. Low-degree section surfaces follow the waisted rib planform, measured width variation and rounded free end. A rounded crown replaces the flat shaft end. The shaft stays straight and circular. The final rib and crown use the measured negative-Y half mirrored exactly across the XZ plane, preventing a loft-parameterization asymmetry while matching the averaged observed profile. The small asymmetric upper-shaft lean in the scan is not copied into the fitted straight cylinder.

Three rounded annular grooves are centered at Z14.078, 18.116 and 22.151 mm. Source medians over 36 azimuths show approximately 0.20 mm radial relief, with half-depth widths of 0.825, 0.750 and 0.750 mm. Revolved monotone cubic profiles use measured valley radii of 2.360, 2.408 and 2.406 mm. Five shallow transverse grooves cross the extraction rib near Z97, 99, 101, 103 and 105 mm, about 0.10 to 0.13 mm below adjacent crests. A bounded local patch over Z95 to 106 mm samples the measured rounded profiles at 0.10 mm intervals, retaining the accepted crown and lower rib. Both valleys and intervening crests follow the scan. Later shaft texture bands and the longitudinal rib outline do not show supported negative geometry, so they are not cut.

## Reference and uncertainty

The corrected comparison target is scans/stylus-without-blu-tack-corrected.glb, in the same raw coordinate frame and unchanged rigid transform. It preserves 41,294 of the original 97,920 faces. The prior mask had incorrectly excluded 337 gray shaft-reflection faces above the Blu Tack; these are restored. Exact original face indices and target hashes are recorded in references/stylus-reference-mask.json and references/stylus-fit.json. The superseded filtered target remains in the local development archive and is not required by this project.

Observed-region comparisons exclude the reconstructed attachment interval, approximately Z35.74 to 64 mm. Against the corrected target, the final grooved model's 95th-percentile surface distances are 0.143 mm scan-to-CAD and 0.142 mm CAD-to-scan, with approximately 99% of observed samples within 0.25 mm. Sampled maxima are 0.414 and 0.444 mm. The complete public writing-tip region, Z0 to 15 mm, has regional 95th-percentile distances of 0.063 and 0.064 mm. The three-ring band is approximately 0.058 mm in both directions, and the five-rib-groove outer-face band is 0.083 and 0.096 mm. Ungrooved observed shaft surfaces are about 0.054 mm in both directions. These are bidirectional sampled results, not a claim that every point or the obscured shaft was measured to 0.25 mm.

## Fit and exports

The Pilot's nominal hidden nose follows the ungrooved smooth writing-tip master with a 0.1001 mm normal offset. Twelve sampled withdrawal poses show zero overlap; exact minimum clearance at the seated and +0.25 mm poses is approximately 0.10 mm. The shaft bore has a 0.20 mm diametral allowance. Hidden cavity geometry is nominal, not recovered factory construction.

The stylus is one valid native solid and its actual saved STL is watertight. Whole-part surface symmetry is verified after explicit mirroring. Complete assembly STL files use full-precision ASCII coordinates to preserve tiny valid triangles that collapse when rounded to float32 after placement; the isolated stylus uses the normal binary STL path. Generated STEP/STL/GLB files are written under build/ and are intentionally not committed. The [source and validation notes](../references/MEASUREMENTS.md) summarize the completed independent checks. Earlier geometry, rejected candidates and detailed development artifacts remain in the local development archive.

## Validation lesson

An intermediate global spline passed native validity yet doubled back axially, creating a second radial boundary inside the tip. That candidate was rejected by exact sections and the bidirectional comparison. The delivered monotone meridian has a single radial boundary through the taper. A separate loft parameterization artifact introduced a small crown asymmetry despite symmetric input profiles; explicit half mirroring corrected it. Saved-mesh, native-section and mirrored-surface checks supplement native validity.

## Don't

Do not restore Blu Tack, the invented open clip slot, a flat rectangular head, or the rejected axial spline reversal. Do not bend the shaft to hide registration or scan asymmetry. Preserve the raw textured source and its fixed transform. Do not describe nominal hidden cavity clearance as OEM verified.

## Changelog

2026-09-30: Added the three measured annular grooves and five transverse grip grooves, preserving exact symmetry and verified 0.10 mm assembly clearance.

2026-09-30: Corrected the comparison mask, reconstructed the rounded writing tip and continuous waisted extraction rib/head from original scan sections, and verified the separate stylus and its seated/withdrawn fit.
