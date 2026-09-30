# front

## What it is

A reconstructed H3800-style front shell. A continuous cubic spline surface wraps across the face and both short ends. Its CAD faces are partitioned at the return transitions to keep Boolean trimming reliable, then represented as exact NURBS surfaces so STEP retains the trimmed seat faces. It includes the asymmetric stylus shoulder, sculpted navigation area, curved speaker crown, rounded long rails, display and control apertures, five speaker slots and simplified connector openings.

## Design notes

The source scan sets the dimensions. Photographs from the iXBT 3850 review and The Gadgeteer 3835/3850 review identify the separate speaker cap and the compound end curves; URLs and inspection notes are in references/photo-sources.json. The exact SKU is unconfirmed. The source coordinates remain provisional millimetres.

The exposed long-edge seam is Z=-4.3, separate from the PCB top at -7.5. The width parameter measures the basic body before its stylus shoulder, which adds about 4.3 mm on one side. The inner shell uses a nominal 1 mm thickness and a 0.2 mm board allowance. Its underside return follows the registered back curvature, and a shared rear-cover outline cuts the seat with a 0.2 mm nominal clearance. The lower end walls stay outside this perimeter. Control and grille holes stop below the front skin; they do not cut through the underside return. The dock opening leaves a lower rim. Four inferred mounting posts use the registered bore pattern. Hidden walls, post details and port edges need physical confirmation for replacement-part use.

The complete front is exported as one solid. The assembly divides that solid into Front and Speaker cap along the visible material boundary. These are nominal touching regions for visual inspection, not a newly designed detachable joint.

## Don't

Do not replace the continuous end curves with vertical walls or stacked ruled loft sections. Do not let automatic chord-length fitting move the measured stations. Do not use the PCB plane as the exterior case seam. Preserve the fixed scan transform and the original sources.

## Changelog

2026-09-30: Added nine internal receivers matching the rebuilt back's asymmetric rim catches, with 0.2 mm nominal clearance. Restored the lower wrap around the asymmetric back shoulder with a shared 0.2 mm lateral receiver and 0.25 mm underside relief. The fixed scan alignment is unchanged.
