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

Symmetry checks reflect samples from the actual final trim edges and trimmed face interiors onto the solid's boundary shell. Across 994 edge points and 2,333 face points, maximum reflected distance is 5.5e-7 mm. This includes the pocket boundaries, rather than testing only their untrimmed support surfaces.

Actual STEP sections were intersected with four recorded local planes and compared with both aligned scan sides. The complete small-profile interval is 0 to 5.5 mm below the narrow-edge tip; the retaining-lip interval is 2.2 to 4.2 mm. Distances below are 95th-percentile contour residuals in millimetres.

| Narrow Vision Pro section | Complete CAD→scan | Complete scan→CAD | Lip CAD→scan | Actual projection |
| --- | ---: | ---: | ---: | ---: |
| Forehead | 0.13 | 0.13 | 0.07 | 0.45 |
| Temple | 0.21 | 0.24 | 0.21 | 0.37 |
| Cheek | 0.15 | 0.19 | 0.14 | 0.26 |
| Nose | 0.06 | 0.07 | 0.07 | 0.55 |

[The exact-CAD section comparison](../references/vision-pro-narrow-lip-sections.png) shows the final profile against both scan sides. These residuals measure agreement with the supplied mesh, not physical fit tolerance: native scan triangle edges are approximately 0.45 mm, and opposing scan sides differ. The source scan's cloth-obscured broad nose saddle remains a regularized smooth contour. Physical mating fit is unverified.

`references/validate_reconstruction.py` reopens all exports, checks final trimmed-boundary symmetry and pocket floor positions, and exercises both fit offsets. `references/validate_narrow_lip_sections.py` reproduces the actual STEP-section comparisons. Fresh main validation writes `build/reconstruction_validation.json`; source data and numeric section evidence are retained under `references/`.

## Reference and alignment

The original `references/source/Light seal.ply` and `Light seal.png` remain byte-for-byte preserved. The original converter retains the UV atlas and embeds the unchanged texture in `scans/vision-pro-light-seal-13w-reference.glb`, removing only detached specks. The scan is not warped, rescaled, or regenerated for this change.

The card's rigid matrix maps the original textured GLB into the symmetric CAD frame. Only the bilateral-plane normal and offset were fitted, using stable hard shell/rim surfaces and excluding the cloth region. Reflected-surface median residual improved from 0.562 to 0.195 mm, and its 95th percentile from 1.621 to 0.499 mm. The same matrix and fitting mask are recorded in `measurements.toml` and `references/alignment.json`.

## Printing and scope

The model remains in inspection alignment. Printing needs a chosen orientation and supports. The check reports a 0.19 mm thin-section warning at (60.1, 33.5, 23.4) on the tiny narrow retaining lip, plus overhang and stability findings in this inspection orientation. The pocket floors are separate and retain at least 3.23 mm at the checked sample points. The small scan-derived lip has not been thickened to satisfy a generic print threshold. The reconstruction includes the two functional outer interfaces and cushion pockets. Black cloth, deep interior lining/support shoulders, fine ribs, magnets, cosmetic seams, and texture relief remain outside scope.
