# Corrected Light Seal interfaces

The narrow high-W rim connects to Vision Pro. Its requested feature is the small retaining lip within 5.8 mm of the leading edge. The broad low-W side connects to the face cushion and has eight shallow closed pockets. Earlier interface labels were reversed; their broad-side profile statistics must not be reused as narrow-side accuracy claims.

`vision-pro-narrow-lip-sections.png` and its metrics compare actual final STEP-plane intersections with the aligned scan, including both mirrored sides. The image is sampled from exact B-rep section edges, not construction guides. `vision-pro-narrow-lip-guides.json` records the sparse measured profile frames; `vision-pro-narrow-reference-sections.json` and `vision-pro-narrow-profile-samples.json` retain the measured paths used for reproducibility. Native scan edge lengths are about 0.45 mm. Submillimetre residuals are reconstruction evidence, not physical fit certification.

`face-cushion-wide-seating-measurements.json` and `face-cushion-wide-return-guides.json` retain the correctly relabeled source measurements for the broad contact surface. Prior mislabeled headset section reports are superseded and removed.

`face-cushion-wide-pockets.json` records paired floor centers, support centers, outward normals, long axes, opening dimensions, depths, and uncertainty. Floor and support centers differ by the measured depth along the outward normal. The pocket map and measurement summary show the eight scan-supported depressions. Dark texture without matching depression is excluded.

Run `python references/validate_reconstruction.py` after exporting the default STEP, STL, and 3MF. It checks one connected body, export manifoldness, symmetry of the actual trimmed boundary including pocket edges, measured floor positions, and small nonzero fit offsets. Run `python references/validate_narrow_lip_sections.py` to reproduce the section metrics from the default STEP.

`alignment.json` preserves the original rigid mirror-plane fit. Original PLY, texture, textured GLB, and converter are unchanged. The original datum is corrected by one proper rigid matrix, with no scale, warp, or scan mirroring.

`face-cushion-wide-pocket-review.json` and `face-cushion-wide-pocket-thickness.json` verify actual exported floors and their sampled remaining material. `face-cushion-wide-final-cad.png` shows all eight finished pockets. The 0.19 mm automatic thin-section finding is on the small narrow retaining lip, remote from these pocket floors.
