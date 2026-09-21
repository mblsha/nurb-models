# Vision Pro Light Seal 13W

A smooth, exactly bilateral reconstruction of the rigid shell with the headset-facing inverse-T interface and the cushion mating rim. The black nose cloth and interior intricacies are outside its scope.

```toml
target = { file = "scans/vision-pro-light-seal-13w-reference.glb", units = "mm", tolerance_mm = 1.0, transform = [0.9998502805779668, -0.016453468760646264, -0.005357218859038693, 0.24252042023653497, 0.016453468760646264, 0.9998646315492281, -4.407571606593663e-05, 0.0, 0.005357218859038693, -4.407571606593663e-05, 0.9999856490287387, 0.0, 0.0, 0.0, 0.0, 1.0] }
```

## Geometry

The headset interface has a broad, asymmetric seated foot, a narrow raked stem, and overhang on both sides of the stem. Its flat contact face follows measured local seating planes, with transverse contact runs of approximately 17.2 mm at the forehead, 15.0 mm at the temple, and 13.0 mm at the cheek. The orientation changes around the rim; it is not a uniform section swept in a global plane. The foot tapers into the narrow hard nose region, where cloth obscures some of the original geometry. The rounded return caps and stem shoulders follow paired hard scan contours through the first 8 mm of seating-normal depth, using seven regularized anchors on each side. Internal ribs and recesses remain omitted.

One half of every guide and seating frame defines the model; the opposite half is its exact reflection about X = 0. Explicit periodic cubic B-splines avoid the asymmetric seam tangent chosen by the kernel's automatic interpolator. The shell and interface are sewn into one solid with six smooth faces. The cushion retains its previous smooth shape after symmetric alignment and pairing. `wall_mm` controls the nominal middle wall; the two fit offsets provide small calibration adjustments to the mating loops.

## Scan alignment

The original textured scan stays unchanged. A rigid transform aligns its fitted bilateral plane with model X = 0, without scaling or warping. The fit uses stable hard shell and rim surfaces, selected by texture luminance and excluding the cloth-obscured nose region. Only the mirror-plane normal and offset were optimized. The plane correction is approximately 0.99° with a 0.243 mm X translation. Reflected-surface residual improved from a 0.562 mm median and 1.621 mm 95th percentile to 0.195 mm and 0.499 mm. The canonical matrix is stored in this card and `measurements.toml`.

## Verification and fit evidence

The default part is approximately 161.43 × 96.06 × 85.27 mm. STEP reopens as one valid solid; STL and 3MF each reopen as one watertight connected mesh. The complete B-rep has 1.42e-13 mm maximum reflected-surface deviation across 2,430 samples. Display/export triangulations approximate these exact symmetric surfaces and can use different triangles on opposite sides.

The actual B-rep contact face was sampled at 720 points across nine observable sections: median deviation is 0.085 mm, the 95th percentile is 0.218 mm, and the maximum is 0.632 mm. All samples lie within 1 mm of the aligned scan. The eight worst accelerated results match exhaustive triangle search exactly.

The local section comparison distinguishes the contact face from the complete hard flange profile. Values below are 95th-percentile contour distances in millimetres; the profile region covers the measured seating span plus 2 mm at either end and seating-normal depth from -2 to 8 mm.

| Section | Contact CAD→scan | Contact scan→CAD | Profile CAD→scan | Profile scan→CAD |
| --- | ---: | ---: | ---: | ---: |
| Forehead | 0.15 | 0.17 | 0.30 | 2.19 |
| Temple | 0.19 | 0.25 | 0.91 | 1.12 |
| Cheek | 0.16 | 0.47 | 0.35 | 0.47 |

The forehead reverse-profile outlier comes from the intentionally omitted inner contour near 8 mm depth, beyond the narrow mating return. The temple return differs between the two scan sides; the symmetric reconstruction uses their smooth paired contour. The plain interior beyond the mating profile remains simplified. `references/headset-section-comparison.png` shows the final CAD against both scan sides and the earlier flat rim; its numeric evidence is in `references/headset-section-metrics.json`.

The headset's observable guide curve has 0.236 mm median and 0.622 mm 95th-percentile deviation from the aligned scan. The cushion guide has 0.220 mm median and 1.101 mm 95th-percentile deviation. These guide statistics supplement the local profile comparison; they are not measurements of physical mating tolerance. The rear nose guide is reported separately because the rigid saddle is obscured: its regularized curve reaches 6.57 mm from visible scan geometry. Physical fit remains unverified.

`references/validate_reconstruction.py` reopens exports, applies the saved rigid alignment, checks actual B-rep symmetry, and measures the mating guide curves. Detailed evidence is in `measurements.toml`; fresh validation writes `build/reconstruction_validation.json`.

## Source and texture

The original `references/source/Light seal.ply` and `Light seal.png` remain byte-for-byte preserved. `references/source/convert_reference.py` retains the original UV atlas, removes only detached scan specks, and embeds the unchanged texture into `scans/vision-pro-light-seal-13w-reference.glb`. The source GLB uses the original U/V/W datum. The card transform maps that reference into the symmetric CAD frame.

## Printing and omissions

The model remains in inspection alignment. Its curved base and unsupported surfaces require a chosen print orientation and supports; the current thin-wall check passes. Black nose-guard cloth, fine internal ribs, magnets, recess details, texture relief, and cosmetic seams are intentionally absent.
