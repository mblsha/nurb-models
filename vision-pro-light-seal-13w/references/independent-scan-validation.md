# Independent Light Seal scan evidence

Current scan-agreement status: **needs_review**. Construction regressions and physical fit are separate verdicts. These checks can reject a model whose authored dimensions and symmetry tests pass.

Reference contours are independently re-extracted for both sides. Pocket neighborhoods use retained centers and local axes but never use authored slot lengths or widths. A robust quadratic support fit and a 0.22 mm depression threshold define the raw boundary. Soft edge segmentation and registration remain measurement uncertainties. A contour that reaches its neighborhood boundary is unknown, not accepted.

Between-guide rim planes sit halfway between construction stations 2/3, 6/7, and 9/10. Broad seating checks use retained measured frames and fresh raw mesh sections. Every CAD contour is an exact B-rep section sampled at 0.04 mm; scan contours are mesh-plane intersections. Thresholds are 0.45 mm for the narrow scan, 0.75 mm for broad seating, and the retained 0.4 or 0.5 mm pocket dimension uncertainty. None is a physical mating tolerance.

| Region | Side | CAD to scan p95 mm | Scan to CAD p95 mm | Verdict |
| --- | --- | ---: | ---: | --- |
| P1 | right | 1.435 | 1.520 | needs_review |
| P1 | left | 1.261 | 1.260 | needs_review |
| P2 | right | 2.735 | 3.165 | needs_review |
| P2 | negative_X | unknown | unknown | unknown |
| P3 | right | 2.911 | 2.910 | needs_review |
| P3 | left | 2.710 | 2.710 | needs_review |
| P4 | right | 1.434 | 1.484 | needs_review |
| P4 | left | 1.580 | 1.630 | needs_review |
| seat_2 | right | 0.130 | 0.130 | within_scan_uncertainty |
| seat_2 | left | 0.120 | 0.121 | within_scan_uncertainty |
| seat_4 | right | 0.204 | 0.204 | within_scan_uncertainty |
| seat_4 | left | 0.245 | 0.258 | within_scan_uncertainty |
| seat_6 | right | 0.272 | 0.300 | within_scan_uncertainty |
| seat_6 | left | 0.216 | 0.216 | within_scan_uncertainty |
| seat_8 | right | 0.338 | 0.379 | within_scan_uncertainty |
| seat_8 | left | 0.475 | 0.475 | within_scan_uncertainty |
| rim_2_3 | right | 1.287 | 1.256 | needs_review |
| rim_2_3 | left | 1.097 | 1.093 | needs_review |
| rim_6_7 | right | 1.171 | 1.149 | needs_review |
| rim_6_7 | left | 1.493 | 1.470 | needs_review |
| rim_9_10 | right | 0.106 | 0.107 | within_scan_uncertainty |
| rim_9_10 | left | 0.129 | 0.134 | within_scan_uncertainty |

The new findings require geometric review of the narrow lip between guides and the difference between cushion floor footprints and softened opening boundaries. The retained scan supports these investigations; it does not establish manufactured fit. Do not widen acceptance thresholds merely to make these checks pass.
