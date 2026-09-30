# Palm Pilot Professional source and validation notes

All dimensions are provisionally millimetres. The body and stylus retain the fixed raw-scan registration matrices in their part cards. Original PLY/PNG files, imported reference GLBs and their source hashes are included under scans/. The model uses embedded measured parameters and does not load a generated mesh, audit report or profile file to construct its CAD.

## Observed exterior

The front chin is intentionally asymmetric. Its main and left apron curves are tangent circular arcs fitted to the source, with the lowest portion offset toward positive X. Large-radius side walls blend into rounded front and rear edges. The measured display opening below its rim is 59.623 by 80.551 mm. Four application buttons use source-derived spherical domes. The scroll keys have approximately 13 mm outward arcs, flatter facing inner edges and broad low crowns. Their matching casing wells follow the curved footprints.

The upper memory door spans approximately X −36.0 to 31.6 and Y 11.0 to 59.0. It slides toward +Y and carries the foot near (−32.1, 52.3); the opposite upper foot stays fixed. The lower battery door spans approximately X −40 to 12.8 and Y −40.15 to −14.8, slides toward −X, and wraps the left rear edge to about Z 4.6. Its D-shaped thumb dish is about 7.8 by 12.4 mm and 0.48 mm deep. The memory bulge is a continuous surface region within the larger door.

Door identities and directions agree with the [1997 PalmPilot Handbook, pages 9–10](https://cybarcode.com/sites/cy/files/manuals/palm/palm_pilot_user_manual.pdf) and the original-device [memory-door](https://guide-images.cdn.ifixit.com/igi/xfIjTNBuhCYWlKoi.medium) and [battery-door](https://guide-images.cdn.ifixit.com/igi/EhoocUMBfcgTBPrV.medium) removal photographs.

The paired docking mouths are mirrored across X=0. They span approximately Y −57.5 to −54.7 and Z 7.65 to 11.99 with a small seam-level flare. Source groove roots near |X|36.6 show material behind the exterior seam. Local rear-owned backing restores that shallow groove, and the shared socket cutter leaves a continuous side entry. The blind closure at |X|35.0 is nominal because source triangles do not resolve a reliable OEM floor.

## Stylus and cavity

The straight fitted shaft is 5.180704 mm in diameter; the observed tip-to-head length is 107.368 mm. The rounded writing tip follows a 15 mm monotone revolved meridian. A solid waisted extraction rib and rounded head reproduce the original surface. The completed shape uses one measured half mirrored across Y=0. Three annular grooves are centered at Z 14.078, 18.116 and 22.151; five shallow transverse rib grooves lie near Z 97, 99, 101, 103 and 105. The interval Z 35.74–64 is obscured by Blu Tack and reconstructed as a plain fitted cylinder.

The corrected stylus reference keeps 41,294 of 97,920 original faces, including 337 genuine gray shaft-reflection faces restored after the first mask. Exact source indices, transformations and hashes are preserved in [stylus-reference-mask.json](stylus-reference-mask.json) and [stylus-fit.json](stylus-fit.json).

The case passage axis is X 36.0517, Z 6.8262 along Y. Source entrance arc fits yield radii about 2.57–2.61 with residuals 0.034–0.044, insufficient to establish a manufactured running clearance. The bore therefore uses an explicit nominal radius of 2.690352, giving 0.10 radial clearance. Its smooth ungrooved nose master has 0.1001 normal and axial allowance. The tapered external lips, rounded keyway start and asymmetric mouth roll follow the scan; small internal relief maintains straight withdrawal. Stylus grooves are not negatively copied into the cavity.

## Nominal hidden construction

Only the closed exterior is scanned. Cover backing thicknesses, empty slide seats, 0.20 mm seam/seat allowances, concealed key skirts and well depths, blind socket floors, and the interior stylus running envelope are model choices. Battery translation is (−d, 0, −0.004146d); memory translation is (0, d, 0.0085d), following the rear datum. Neither empty seats nor finite motion checks establish factory internals or manufactured fit. There are no invented guide rails, hooks, contacts, batteries, electronics or button mechanisms.

## Completed reconstruction checks

The accepted full assembly has seventeen valid positive native solids. Each removable cover and the isolated stylus is one connected solid. Eighteen sampled cover-travel states had zero overlap with the fixed case and the other seated door. Twelve sampled stylus-withdrawal poses had zero overlap; exact seated and +0.25 mm minimum distances were approximately 0.100 mm. These are finite-pose checks, not a continuous swept-volume certificate. Both scroll caps have zero overlap with the front casing; the fixed front and rear casings have zero positive common volume, and the paired socket cutter has exact native mirror symmetry.

The final stylus comparison used 12,000 area-weighted surface samples in each direction and excluded the whole obscured interval. Observed scan-to-CAD and CAD-to-scan 95th-percentile distances were 0.143 and 0.142 mm, with sampled maxima 0.414 and 0.444 mm; approximately 99% of samples were within 0.25 mm. The three-ring band had approximately 0.058 mm 95th-percentile distance in both directions, and the transverse rib-groove band had 0.083 and 0.096 mm. The complete 15 mm tip region had 0.063 and 0.064 mm. These selected sampled results are not uniform error bounds.

Scroll-cap section comparisons below the apex generally had 95th-percentile residuals about 0.05–0.21 mm. One near-apex lower-key section reached 0.375 mm, where a small height change strongly changes the tiny contour. This limitation is retained rather than replaced with a blanket tolerance claim. Selected source comparisons at the disappearing rear mouth lip had bidirectional section 95th-percentile distances of 0.120 and 0.113 mm.

Closed, covers-open, covers-removed and withdrawn exports were reopened and checked for native validity and serialized mesh topology. Closed combined STL had 177,580 triangles and twelve closed boundary shells, including four inward-facing enclosed button-well voids. Negative void-shell volumes are not extra physical components. Exact counts can vary with engine tessellation; validity and component ownership are the relevant checks. Detailed development audits, rejected candidates and rendered comparison sheets remain local rather than being committed as generated artifacts.
