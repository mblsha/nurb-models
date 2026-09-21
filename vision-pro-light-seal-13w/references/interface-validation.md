# Revision-bound Light Seal interface validation

Status: **accepted**. Model source `95819604928f`, validator `e3ac6499a5f2`, canonical STEP `25bd3f21c83a`, reference GLB `f26fc3c4e320`, default parameters `30f9ca2cebd2`.

## Symmetry

A geometry-only verification fit from the reference differs from the stored symmetry plane by 0.0043 degrees and 0.0060 mm. The stored plane's reflected-reference p95 is 0.778 mm against a 1.0 mm verification threshold. The final trimmed STEP reflects onto itself with maximum edge and face errors of 5.42e-07 and 1.74e-11 mm.

## Narrow Vision Pro inverse-T interface

Each available scan side is evaluated separately. Complete-profile bidirectional p95 must be at most 0.35 mm; the 2.2 to 4.2 mm inverse-T lip interval must be at most 0.30 mm in both directions.

| Station | Scan side | Complete CAD-to-scan | Complete scan-to-CAD | Lip CAD-to-scan | Lip scan-to-CAD | Projection | Shoulder gain |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| forehead | right | 0.128 | 0.134 | 0.069 | 0.076 | 0.449 | 1.828 |
| temple | right | 0.253 | 0.228 | 0.232 | 0.218 | 0.368 | 2.025 |
| temple | left | 0.270 | 0.248 | 0.215 | 0.250 | 0.368 | 2.025 |
| cheek | right | 0.225 | 0.189 | 0.189 | 0.188 | 0.257 | 1.574 |
| cheek | left | 0.177 | 0.180 | 0.177 | 0.191 | 0.257 | 1.574 |
| nose | right | 0.063 | 0.066 | 0.074 | 0.084 | 0.550 | 1.518 |

## Face-cushion attachment openings

The actual final STEP trim edges are compared on both sides with the pair-averaged scan-derived obround measurements. Bidirectional p95 must be at most 0.05 mm. The separately observed scan-side center disagreement must remain inside each feature's recorded dimensional uncertainty.

| Opening | Side | CAD-to-measured contour | Measured contour-to-CAD | Scan-side center offset | Allowed uncertainty |
| --- | --- | ---: | ---: | ---: | ---: |
| P1 upper_inner | positive_X | 0.020 | 0.019 | 0.348 | 0.400 |
| P1 upper_inner | negative_X | 0.020 | 0.019 | 0.348 | 0.400 |
| P2 upper_lateral_temple | positive_X | 0.020 | 0.019 | 0.159 | 0.400 |
| P2 upper_lateral_temple | negative_X | 0.020 | 0.019 | 0.159 | 0.400 |
| P3 lower_lateral | positive_X | 0.017 | 0.019 | 0.472 | 0.500 |
| P3 lower_lateral | negative_X | 0.017 | 0.019 | 0.472 | 0.500 |
| P4 lower_inner_forehead | positive_X | 0.022 | 0.019 | 0.292 | 0.400 |
| P4 lower_inner_forehead | negative_X | 0.022 | 0.019 | 0.292 | 0.400 |

## Scope and interpretation

The narrow validation covers the small retaining lip through 5.5 mm depth. The face-cushion validation covers the eight finished shallow attachment openings. Black nose-guard cloth, the deep interior, lining shoulders, magnets, ribs, cosmetic seams, and texture relief remain excluded. Scan agreement is reconstruction evidence, not physical fit certification.

Run `python references/validate_interfaces.py` after exporting the default STEP, STL, and 3MF. The JSON result contains thresholds, full per-side statistics, methods, hashes, and limitations.
