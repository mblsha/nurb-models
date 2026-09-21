# Vision Pro Light Seal 13W

A smooth symmetric rigid shell with a small retaining lip on the narrow Vision Pro edge and eight shallow attachment recesses on the broad face-cushion side. The black nose cloth and interior intricacies are excluded.

```toml
target = { file = "scans/vision-pro-light-seal-13w-reference.glb", units = "mm", tolerance_mm = 1.0, transform = [0.9998502805779668, -0.016453468760646264, -0.005357218859038693, 0.24252042023653497, 0.016453468760646264, 0.9998646315492281, -4.407571606593663e-05, 0.0, 0.005357218859038693, -4.407571606593663e-05, 0.9999856490287387, 0.0, 0.0, 0.0, 0.0, 1.0] }
```

## Interface identification

The narrow high-W end connects to Vision Pro. The broad low-W end connects to the soft face cushion. Earlier versions reversed these labels; their broad-flange measurements were cushion-side evidence, not proof of the narrow Vision Pro connection. The corrected source uses `VISION_PRO_NARROW_*` and `FACE_CUSHION_WIDE_*` throughout. [The labeled scan](../references/interface-identification.png) identifies both ends.

## Geometry and controls

The Vision Pro feature is small: a rounded leading edge, a narrow neck, and a retaining projection about 3 mm below the tip. Its paired scan profiles cover only the first 5.8 mm, then join the plain shell. The deeper broad inner shoulder is deliberately omitted. Shape-preserving cubic profile segments preserve the undercut without adding spline bulbs; periodic cubic curves keep the perimeter smooth. The measured projection in the four checked sections is 0.26 to 0.55 mm.

The broad cushion contact retains its smooth measured flange and has four mirrored pairs of shallow obround recesses. These have closed floors in the scan, so they are modeled as blind pockets. Nominal openings are 8.2 to 8.8 mm long, 2.5 to 4.6 mm wide, and 0.86 to 1.02 mm deep. Actual cutters terminate at the paired measured floor centers. [The pocket map](../references/face-cushion-wide-pocket-map.png) and [measurements](../references/face-cushion-wide-pocket-measurements.png) show their locations and dimensions.

One half of every guide and frame defines the opposite half by exact reflection about X = 0. The pocket cutters are also reflected as complete solids. `headset_fit_offset_mm` moves the narrow Vision Pro rim and lip; `cushion_fit_offset_mm` moves the broad cushion contact and its pocket cutters. `wall_mm` controls the nominal middle wall. Both fit offsets passed separate -0.2 and +0.2 mm single-solid builds. The default wall is 1.8 mm.

## Validation

[The final broad-side CAD view](../references/face-cushion-wide-final-cad.png) shows all eight pockets. Each measured floor center lies on its intended planar floor and retains solid material behind it. Five representative ray samples per pocket give minimum remaining material of 3.23, 6.85, 6.09, and 8.87 mm for the four paired locations. These are sampled floor thicknesses, not a global wall minimum.

The final default CAD is one valid solid, approximately 161.43 × 96.06 × 84.98 mm. STEP reopens as one valid solid; STL and 3MF each reopen as one watertight connected mesh. The exact solid has 62 faces and an adaptively integrated volume of 71,024.80 mm³. A 0.04 mm absolute-deflection mesh cache keeps the small lip responsive in the viewer without changing the B-rep.

Symmetry checks reflect samples from the actual final trim edges and trimmed face interiors onto the solid's boundary shell. Across 994 edge points and 2,334 face points, maximum reflected distance is 5.5e-7 mm. This includes the post-boolean pocket boundaries, rather than testing only construction guides or untrimmed support surfaces.

Actual STEP sections were intersected with four recorded local planes and compared independently with every available aligned scan side. The complete small-profile interval is 0 to 5.5 mm below the narrow-edge tip; the inverse-T lip interval is 2.2 to 4.2 mm. Complete-profile bidirectional p95 must be no more than 0.35 mm and lip bidirectional p95 no more than 0.30 mm. The CAD projection must remain between 0.20 and 0.65 mm and the rim must widen by at least 1.0 mm from neck to shoulder. Distances below are 95th-percentile contour residuals in millimetres.

| Narrow Vision Pro section | Scan side | Complete CAD→scan | Complete scan→CAD | Lip CAD→scan | Lip scan→CAD | Actual projection |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Forehead | Right | 0.128 | 0.134 | 0.069 | 0.076 | 0.449 |
| Temple | Right | 0.253 | 0.228 | 0.232 | 0.218 | 0.368 |
| Temple | Left | 0.270 | 0.248 | 0.215 | 0.250 | 0.368 |
| Cheek | Right | 0.225 | 0.189 | 0.189 | 0.188 | 0.257 |
| Cheek | Left | 0.177 | 0.180 | 0.177 | 0.191 | 0.257 |
| Nose | Right | 0.063 | 0.066 | 0.074 | 0.084 | 0.550 |

[The exact-CAD section comparison](../references/vision-pro-narrow-lip-sections.png) shows the final profile against both scan sides. The older side-pooled image metrics are visualization only; the table and revision-bound JSON use independent sides. These residuals measure agreement with the supplied mesh, not physical fit tolerance: native scan triangle edges are approximately 0.45 mm, and opposing scan sides differ. The source scan's cloth-obscured broad nose saddle remains a regularized smooth contour. Physical mating fit is unverified.

Each finished cushion opening is also checked on both CAD sides. The final STEP trim edges are within 0.028 mm bidirectional p95 of their scan-derived pair measurement, below the 0.05 mm threshold. Reflected opening pairs are within 0.025 mm p95, and the independently observed scan-side center disagreement remains inside each feature's recorded 0.4 or 0.5 mm uncertainty. The retained measurement does not include raw independent per-side opening polylines, so this is not a claim of per-side raw contour agreement.

`references/validate_reconstruction.py` reopens all exports, checks final trimmed-boundary symmetry and pocket floor positions, exercises both fit offsets, and runs `references/validate_interfaces.py`. The interface validator regenerates `references/interface-validation.json`, `references/interface-validation.md`, and the narrow acceptance JSON with model, validator, measurements, thresholds, export, reference, alignment, and default-parameter hashes. It writes these canonical artifacts only after every child passes. `references/validate_narrow_lip_sections.py` remains useful for the visual section plot; its JSON outputs are machine-labelled `superseded_visualization_only`, and current per-side acceptance lives in `interface-validation.json`. `references/test_validator_regressions.py` proves a bad retained scan side fails under normal and optimized Python without replacing accepted evidence.

## Reference and alignment

The original `references/source/Light seal.ply` and `Light seal.png` remain byte-for-byte preserved. The original converter retains the UV atlas and embeds the unchanged texture in `scans/vision-pro-light-seal-13w-reference.glb`, removing only detached specks. The scan is not warped, rescaled, or regenerated for this change.

The card's rigid matrix maps the original textured GLB into the symmetric CAD frame. Only the bilateral-plane normal and offset were fitted, using stable hard shell/rim surfaces and excluding the cloth region. The original fitting assessment improved reflected-surface median residual from 0.562 to 0.195 mm and p95 from 1.621 to 0.499 mm. A separate deterministic geometry-only verification fit differs from the stored plane by 0.0043 degrees and 0.0060 mm; its independent stored-plane reflection p95 is 0.778 mm against a 1.0 mm threshold. The same rigid transform and fitting mask are recorded in `measurements.toml` and `references/alignment.json`.

## Printing and scope

The model remains in inspection alignment. Printing needs a chosen orientation and supports. The check reports a 0.19 mm thin-section warning at (60.1, 33.5, 23.4) on the tiny narrow retaining lip, plus overhang and stability findings in this inspection orientation. The pocket floors are separate and retain at least 3.23 mm at the checked sample points. The small scan-derived lip has not been thickened to satisfy a generic print threshold. The reconstruction includes the two functional outer interfaces and cushion pockets. Black cloth, deep interior lining/support shoulders, fine ribs, magnets, cosmetic seams, and texture relief remain outside scope.
