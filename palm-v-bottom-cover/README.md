# Palm V complete exterior and partial case models

This project reconstructs the Palm V from three supplied scans: the MAF THREE aluminium back-cover project, the separate black plastic intermediate body, and a rough scan of the assembled device. The primary model is [`palm_v_complete`](parts/palm_v_complete.py), a whole-device exterior with smooth nominal surfaces and bilateral main forms. The earlier partial case models and assembly remain available as historical design work. Glue, scan noise and accidental bends are excluded from the nominal CAD; the original observations remain unchanged.

## Primary complete exterior

[`parts/palm_v_complete.py`](parts/palm_v_complete.py) is the current entry point. It combines 30 separately named solids, including the independently fitted metal shells, smooth paired stylus/accessory channels, display, measured curved scroll rocker, four application keys, power and contrast controls, and rear docking features. Its [part card](parts/palm_v_complete.md) distinguishes measured exterior details from nominal hidden backing and records the intentionally asymmetric controls. The [frozen complete-exterior review](references/complete-exterior-review/) preserves the reviewed evidence and preview.

From this project directory:

```bash
nurb build palm_v_complete
python references/export_complete.py
python references/serve_complete.py .
```

The complete exterior does not use the historical `palm_v_body` intermediate chassis. Its dedicated [`palm_v_complete_frame`](parts/palm_v_complete_frame.py), [`palm_v_complete_front`](parts/palm_v_complete_front.py) and [`palm_v_complete_scroll`](parts/palm_v_complete_scroll.py) sources preserve the whole-scan side channels and updated scroll geometry. Hidden electronics, exact switch mechanisms and unresolved attachment construction are outside the reconstruction. Colors indicate plausible material groups, not scanner color measurements.

## Preserved partial models

These six earlier parts remain separately editable. Fresh default-parameter builds on 2026-10-01 confirmed the statuses below directly from their Python sources; an old STEP was not used as a substitute for a successful build.

| Part | Purpose | Current source status |
| --- | --- | --- |
| [`palm_v_bottom_cover`](parts/palm_v_bottom_cover.py) | Nominal rear aluminium cover with independent sheet and rim evidence | Builds one valid solid; reused by the complete exterior |
| [`palm_v_body`](parts/palm_v_body.py) | Separately scanned plastic intermediate chassis, internal tabs and historical seating interfaces | Fails the rear seating guard at the default 0.65 mm gauges |
| [`palm_v_front_cover`](parts/palm_v_front_cover.py) | Earlier provisional front shell inferred from the assembled scan | Builds one valid solid; retained beside the revised complete-model front |
| [`palm_v_display`](parts/palm_v_display.py) | Visible display insert with provisional hidden thickness | Builds one valid solid; reused by the complete exterior |
| [`palm_v_scroll_button`](parts/palm_v_scroll_button.py) | Earlier hourglass scroll key used by the tilted historical assembly | Builds one valid solid; superseded in the complete exterior by the measured curved rocker |
| [`palm_v_button`](parts/palm_v_button.py) | Round application key | Builds one valid solid; reused by the complete exterior |

[`parts/palm_v.py`](parts/palm_v.py) preserves the earlier assembly of those parts. It depends on `palm_v_body`, so its current source cannot build a complete assembly. The body raises `Rear interface separated substantial body material; inspect the chosen gauge` after the nominal rear-interface cut. That diagnostic is preserved rather than hidden by loosening its material-loss guard or changing a measurement merely to obtain a passing build. Unscoped `nurb build` also attempts this historical body; use a named part when building a working model.

The first back-cover reconstruction was rejected and is preserved under [`references/rejected-v1/`](references/rejected-v1/). Its deficiencies and process recommendations are recorded in [`references/audit-v1.md`](references/audit-v1.md). Commit `860030e` preserves the reviewed curved rebuild before the requested rim straightening.

The retained [`palm_v_bottom_cover`](parts/palm_v_bottom_cover.py) forms a nominally planar broad sheet from measured sections, preserves the localized raised form around the slot and Reset opening, forms the inner surface with a normal sheet offset, mirrors the actual half-solid about the long center plane, and cuts the central slot and offset Reset hole. The -Y split form and curved perimeter bends are retained. Glue and fixtures are excluded from the CAD.

## Symmetry and mating intent

X=0 is the upright longitudinal symmetry plane. It is fitted to corresponding outer scan geometry, rather than the mass centroid of asymmetric internal tabs. The main case envelope is exactly mirrored left to right; supported functional asymmetries, including the Reset hole and plastic attachment features, are retained. Front and rear profiles are measured independently and are not mirrored through the thickness.

The historical plastic body was designed to derive its rear seats from the aluminium back's inner surface in their shared assembly pose, with zero nominal clearance along selected seating runs and no positive-volume overlap. Its source currently stops at the rear seating guard, so that design intent is not a current successful mating result. Interior cavities stay open, and the historical assembly passes the rear sheet thickness into both components. Old contact reports describe only their recorded STEP hashes, not every later edit or this failing source revision. Even a successful nominal CAD contact would not establish physical fit or a manufacturing clearance recommendation.

## Measured shape versus nominal shape

The observation-derived surface is saved in `references/surface-fit.json`. The default nominal model places most of the broad aluminium field in the exact plane Z = -0.30 mm. The only intentional departures are the localized raised form around the slot and Reset opening, the -Y split-end form, and the perimeter bends. The scan has a shallow longitudinal bow and transverse crown; removing them is an owner-requested manufacturing-intent inference rather than proof of the original drawing. The normal sheet thickness is applied after reshaping. With `straight_rims=True`, the planar field remains nominal regardless of `longitudinal_straightening`; use `straight_rims=False` with `longitudinal_straightening=0` to inspect the earlier observation-derived shape.

Independent side-strip fits find about 0.30–0.35 mm midspan bow over 88 mm. Straightening is a deliberate idealization: a scan of a potentially bent piece cannot prove which small departures came from the original manufacturing design. The original observations remain unchanged for comparison. Source fit and intentional correction must not be conflated.

The nominal sheet gauge is provisionally 0.65 mm, supported by paired interior/exterior observations near 0.65–0.70 mm. Adhesive, residual registration error, and variation between observed patches prevent a metrology claim. The central slot is approximately 7.2 × 2.7 mm, and the Reset bore is provisionally 1.8 mm. These dimensions require physical measurement for manufacturing or guaranteed mating fit.

`straight_rims=True` constrains the five marked rear rim cores to straight, level physical runs and enforces the broad planar field while retaining curved bend cross-sections and smooth corner transitions. The split end returns retain the measured angle in plan view. Set it to `False` to inspect the earlier unconstrained rim fit. See the back-cover card for fitted line equations and core extents.

## Evidence and reproduction

The [frozen complete-exterior review](references/complete-exterior-review/) contains the reviewed whole-device evidence and preview. Its reports identify the exact geometry they measured. Current rebuilds generate new exports and validation in `build/`; a frozen report does not automatically validate a later source edit.

- `scans/palm-v-bottom-cover-back-observed.ply.gz` retains 495,454 measured, unmirrored exterior points.
- `scans/palm-v-bottom-cover-comparison-triangles.ply.gz` retains 740,708 original triangles from a complete exterior observation plus selected side-rim observations. It adds no synthetic closure or remeshing.
- `scans/palm-v-body-observed.ply.gz` preserves the supplied plastic-body PLY byte-for-byte inside gzip.
- `scans/palm-v-rough-observed.ply.gz` preserves every original whole-device STL triangle, facet normal, attribute word, and source face order using exact vertex indexing.
- `references/palm-new-reference-frames.json` records the fixed bilateral coordinate frames. The original scans are not resampled or symmetrized to make the CAD appear more accurate.
- `references/palm-assembly-poses.json` records the rear cover's rigid assembly placement. It is fitted from original observations, then applied unchanged to the nominal straightened cover.
- `references/import-alignment.json` and `references/original-triangle-provenance.json` preserve source hashes, supplied group registration, the common coordinate frame, and exact selection rules.
- `references/observed-fit-baseline.json` records independent diagnostics for the observation-derived reconstruction before nominal straightening. Its STEP hash identifies the version measured; it is not a report for the straightened default.
- `references/straightening-support.json` and `references/thickness-evidence.json` document the nominal correction and gauge evidence.
- `references/audit_step_geometry.py` probes the reopened STEP independently of the part's fitting code. `references/audit_observed_fit.py` compares a specified STEP with original observations using recorded regions, seeds, and source hashes.

`references/complete-frame-fit.json` records the mirrored whole-device side-channel sections, and `references/complete-rocker-observations.json` preserves the observed scroll-control center section. Regenerate the complete frame fit with `python references/fit_complete_frame.py`; `python references/export_complete.py` rebuilds the complete named assembly and checks its STEP, GLB and STL exports. The export uses absolute 0.025 mm tessellation and native surface normals, with closer angular sampling on the long side channels.

`references/README.md` explains source reproduction and the limitations of the observed mesh. The side-region mask can retain some adhesive, and source meshes contain open boundaries and overlapping observations. A low sampled distance alone does not establish correct thickness, topology, or physical fit.

## Review

Use `python references/serve_complete.py .` to start the normal watched viewer with only `palm_v_complete` in its initial build queue and the reviewed absolute display tessellation. The script prints its URL and supports `--port` when another instance already occupies the default port. A shared-source save can still rebuild other parts. The desktop app and standard `nurb dev` also support this project; select `palm_v_complete` for the current exterior, and expect the historical body to report its known failure if all parts are built.

Select `palm_v_bottom_cover`, `palm_v_front_cover`, `palm_v_display`, `palm_v_scroll_button` or `palm_v_button` to inspect the retained partials independently. The `palm_v_body` source remains available for diagnosing the historical seating interface, and `palm_v` preserves the earlier assembly definition. Use component visibility, comparison views, and longitudinal/transverse sections to inspect the formed shape and interfaces. The original source and nominal models share recorded fixed coordinate frames; no extra best-fit transform is applied to hide a nominal correction.

Current complete-model exports and validation live in `build/palm_v_complete.*`, `build/palm_v_complete-validation.json` and `build/palm_v_complete-comparison.json` when generated. The STEP preserves named separate solids. The STL preserves separate component shells and is not a certified fused, print-ready body. FDM printability checks are separate from fidelity to the original thin aluminium part. Neither the complete exterior nor the historical partials have been physically fitted to a Palm V.

### Historical rear/body mating evidence

The older `build/rear-body-contact-audit.json` checks reopened rear and plastic-body STEP solids in their recorded assembly pose. Those historical reports recorded 177 seating contacts within 0.01 mm; `build/rear-inner-edge-contact-audit.json` added 105 contacts immediately inside the continuous-end inner cut edge. Separately, 475 of 475 rays in `build/rear-dense-occupancy.json` found no co-occupied depth above 0.005 mm. These counts are evidence for the STEP hashes in those reports, not a passing result for the current `palm_v_body.py`, which fails before returning a solid. Do not reuse an older `palm_v.step` or body STEP as an export of the current source.

The named-contact report skips global OCCT Common because coincident contact faces can create misleading signed solids; the independent occupancy rays test their sampled lines directly. Across the two lower returns, 24 sampled rays made contact, six lay outside the rear-sheet footprint, and six had no body under existing rear material. The report retains these non-contact samples rather than silently counting them as contacts.

After repairing or changing the historical rear sheet or plastic seat, rebuild both STEP files and rerun `python references/audit_rear_inner_edge_contact.py` from this project root. Run `references/audit_rear_mating.py` with `--rear`, `--body`, `--poses`, `--output`, and `--contact-only`, and `references/audit_rear_dense_occupancy.py` with the same four path arguments. The inner-edge check samples 105 points beneath the +Y hem, while the 475 occupancy rays check for unwanted solid overlap. Inspect report hashes before relying on older results. These sampled CAD checks do not verify physical assembly or every point on the interface.

The historical plastic body's initial STL tessellation had boundary defects and was not a verified export. The current complete exterior uses a separately constructed whole-device frame and does not depend on that failing partial body. A separate front-metal scan is still needed to refine the provisional front rim and hidden details; the existing exterior scan does not establish manufacturing tolerances.
