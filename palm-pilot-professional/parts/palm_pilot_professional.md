# Palm Pilot Professional with sliding rear covers

```toml
target = { file = "scans/import-056f225059e4892abed2/reference-d498d06da15f734ccda2.glb", units = "mm", tolerance_mm = 0.5, transform = [0.982849689950779, -0.03263262594394324, 0.18149820574225992, -0.10564280625083095, -0.17092522887091355, -0.5306316735361307, 0.830189492330318, 0.5452385380979639, 0.06921743349101293, -0.8469741074934037, -0.5271089148711768, 16.616788815329457, 0.0, 0.0, 0.0, 1.0] }

[variants.withdrawn]
note = "Stylus withdrawn by 30 mm."
[variants.withdrawn.params]
stylus_withdrawal = 30.0

[variants.covers_open]
note = "Battery cover slid sideways 25 mm and memory cover slid toward the top 22 mm."
[variants.covers_open.params]
battery_slide = 25.0
memory_slide = 22.0

[variants.covers_removed]
note = "Both rear covers fully clear of the case, with 60 mm outward travel."
[variants.covers_removed.params]
battery_slide = 60.0
memory_slide = 60.0
```

## What it is

An editable reconstruction of the supplied Palm Pilot Professional exterior, now with distinct removable Battery cover and Memory cover parts. The closed main assembly contains seventeen named native components. The upper-left rear foot belongs to the Memory cover and is fused into that single connected part. The other three rear feet remain fixed. The palm_pilot_body download contains only the fixed exterior and controls, excluding both covers and the traveling foot; use the main assembly for comparison with the complete source scan.

## Observed geometry

The broad upper rear panel is the memory door. Its measured outline runs approximately X−36.0 to 31.6, Y 11.0 to the product's upper edge. It includes the previously reconstructed bulged surface and slides toward +Y. The lower battery door runs approximately X−40 to 12.8 and Y−40.15 to −14.8, wraps the rolled left edge to approximately Z 4.6, and slides toward −X. The measured D-shaped thumb dish is about 7.8 by 12.4 mm with a 0.48 mm recession. Narrow seam reveals and rounded inner corners separate both covers from the fixed casing. The measured boundaries and primary manual/repair sources are summarized in the [source and validation notes](../references/MEASUREMENTS.md).

The asymmetric two-arc chin, circular side rolls, curved docking lip, measured display opening and domed application buttons retain the accepted reconstruction. The scroll keys now use scan-derived bowed outward edges, flatter facing edges, rounded ends and broad low crowns; their casing wells follow the same curved footprints. The display opening is 59.623 by 80.551 mm below its rim. Printed markings remain source texture rather than false engraved grooves. The original textured scans and fixed alignment remain unchanged.

The finished eight-groove stylus is unchanged. Its cavity keeps the supported axis X36.0517, Z6.8262 mm along Y. The exposed side keyway now follows measured tapered upper/lower lips and an approximately 1.04 mm rounded start. The mouth has an asymmetric rounded flare and a thin rear lip that disappears before the front lip. Scan-selected circular entrance arcs yield radii of approximately 2.57 to 2.61 mm with 0.034 to 0.044 mm residuals; this is not a reliable manufactured clearance measurement. The running bore therefore retains the explicit nominal radius 2.690352 mm, 0.10 mm beyond the fitted shaft. A small inner keyway relief preserves that functional allowance without widening the outer lip indiscriminately: up to 0.280 mm at the lower root and 0.11 mm at the upper root, blended into the measured outer lips.

The hidden nose now uses a 0.1001 mm normal offset from the same smooth writing-tip master used by the unchanged stylus, joined to the cylindrical extraction envelope. Its axial blind-end allowance is also 0.1001 mm. The annular grooves are not copied into the cavity, so they cannot introduce retaining undercuts. These concealed surfaces are nominal geometry, not recovered OEM interiors. The [source and validation notes](../references/MEASUREMENTS.md) summarize native nearest-wall measurements and finite withdrawal checks; sampled motion is not a continuous swept-volume certificate.

The scroll cap exterior follows measured contours from local Z 18.9 to 20.0, with an approximately 13 mm outward arc and progressively shrinking crown. Corresponding bounded surface patches avoid the folds caused by a global smooth loft. The final tiny crown closure is within 0.01 mm of the fitted peak. Narrow reveals and shallow rolled well rims are observed; concealed skirt/pocket depths are nominal, with no actuation mechanism claimed. Both side dock sockets share an exactly mirrored cutter across X=0, crossing the front/rear casing seam. Their observed mouth is approximately Y −57.5 to −54.7 and Z 7.65 to 11.99, with a slight seam-level flare. The visible walls enter the case; the blind floor at |X|35.0 is an explicit nominal closure because the scan does not resolve an OEM floor. A local rear-owned dock seam backing stops at |X|36.55 and is trimmed against the front casing, leaving a shallow external groove and a continuous socket mouth. No full-case seam redesign or latch hardware is included. Selected source measurements and validation limits are recorded in the [source and validation notes](../references/MEASUREMENTS.md).

## Motion and hidden geometry

battery_slide and memory_slide are positive outward travel in millimetres, from 0 to 60. The battery translation is (−d, 0, −0.004146d); memory is (0, d, 0.0085d), following the measured rear datum. Closed, partly open and fully removed configurations are available in the main assembly. overall_scale scales all geometry uniformly after posing.

Only the closed exterior is scanned. Concealed backing thicknesses, shallow empty seats and 0.20 mm seam/seat clearances are nominal construction choices to make the separate covers movable without overlap. The memory backing is at local Z4.4 and the battery return at local Z4.85. No unseen guide rails, hooks, battery contacts, batteries or electronics are claimed. This is an exterior reconstruction, not a verified OEM replacement enclosure.

## Exports and verification

Normal CLI and viewer downloads include four separate parts: fixed body, Battery cover, Memory cover and stylus. Each cover exports as one connected native solid; the memory foot is included in its cover. export_model.py writes the complete named assembly STEP and combined STL/GLB; --variant covers_open and --variant covers_removed write the posed versions. The combined STL unions contacting body material, combines its validated mesh with the validated local stylus mesh under a double-precision placement, and saves full-precision ASCII coordinates. STEP retains the named components. Constituent files, transforms and hashes are recorded in the assembly export metadata.

Generated STEP/STL/GLB files and export metadata are written under build/ and are intentionally not committed. The [source and validation notes](../references/MEASUREMENTS.md) record the completed reconstruction checks. Historical prototypes and checkpoint exports remain in the local development archive.

## Don't

Do not exchange the battery and memory identities, mirror their directions, detach the memory foot into the fixed body, or restore the obsolete seam around only the upper bulge. Do not restore the rejected twelve-station body loft, symmetric chin, engraved handwriting divider or Blu Tack. Preserve source assets and the fixed alignment. Native validity alone does not establish a valid saved mesh or unobstructed travel.

## Changelog

2026-09-30: Preserved the accepted exterior, separated the full memory and battery doors using measured boundaries, reconstructed the battery edge wrap and finger dish, added outward slide parameters and variants, and added individual cover exports.

2026-09-30: Replaced the generic side slot and conical mouth with scan-derived tapered lips and a local rolled entrance, and rebuilt the hidden blind nose from the unchanged smooth stylus master plus nominal clearance. Preserved the finished stylus, both covers and all unrelated case surfaces.

2026-09-30: Replaced the rectangular scroll caps/wells with measured curved forms and added the paired mirrored blind dock sockets, including local seam backing. Preserved the finished stylus, its cavity and both sliding covers.
