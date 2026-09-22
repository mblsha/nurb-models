# Palm V aluminium back cover

This project reconstructs the nominal, straightened Palm V back cover from the supplied MAF THREE scan archive. The first reconstruction was rejected and is preserved under `references/rejected-v1/`. Its deficiencies and process recommendations are recorded in `references/audit-v1.md`.

The editable model is `parts/palm_v_bottom_cover.py`. It fits a smooth curved exterior from measured sections, forms the inner surface with a normal sheet offset, mirrors the actual half-solid about the long center plane, and cuts the central slot and offset Reset hole. Curved side and end rims are retained. Glue and fixtures are excluded from the CAD.

## Measured shape versus nominal shape

The observation-derived surface is saved in `references/surface-fit.json`. The nominal model removes a coherent shallow longitudinal bow from the panel while preserving the intentional transverse crown, raised central form, and rim curves. The rim moves with the local skin, and the normal thickness is applied after straightening. `longitudinal_straightening=0` retains the observation-derived bow; `1` applies the full nominal correction. The default is `1`, following the request for a straight, symmetric version.

Independent side-strip fits find about 0.30–0.35 mm midspan bow over 88 mm. Straightening is a deliberate idealization: a scan of a potentially bent piece cannot prove which small departures came from the original manufacturing design. The original observations remain unchanged for comparison. Source fit and intentional correction must not be conflated.

The nominal sheet gauge is provisionally 0.65 mm, supported by paired interior/exterior observations near 0.65–0.70 mm. Adhesive, residual registration error, and variation between observed patches prevent a metrology claim. The central slot is approximately 7.2 × 2.7 mm, and the Reset bore is provisionally 1.8 mm. These dimensions require physical measurement for manufacturing or guaranteed mating fit.

## Evidence and reproduction

- `scans/palm-v-bottom-cover-back-observed.ply.gz` retains 495,454 measured, unmirrored exterior points.
- `scans/palm-v-bottom-cover-comparison-triangles.ply.gz` retains 740,708 original triangles from a complete exterior observation plus selected side-rim observations. It adds no synthetic closure or remeshing.
- `references/import-alignment.json` and `references/original-triangle-provenance.json` preserve source hashes, supplied group registration, the common coordinate frame, and exact selection rules.
- `references/observed-fit-baseline.json` records independent diagnostics for the observation-derived reconstruction before nominal straightening. Its STEP hash identifies the version measured; it is not a report for the straightened default.
- `references/straightening-support.json` and `references/thickness-evidence.json` document the nominal correction and gauge evidence.
- `references/audit_step_geometry.py` probes the reopened STEP independently of the part's fitting code. `references/audit_observed_fit.py` compares a specified STEP with original observations using recorded regions, seeds, and source hashes.

`references/README.md` explains source reproduction and the limitations of the observed mesh. The side-region mask can retain some adhesive, and source meshes contain open boundaries and overlapping observations. A low sampled distance alone does not establish correct thickness, topology, or physical fit.

## Review

Run `nurb dev` from this directory and select `palm_v_bottom_cover`. Use the comparison views and longitudinal/transverse sections to inspect the formed shape. The original source and both model settings share the same fixed coordinate frame; no best-fit transform is applied to hide the nominal correction.

Final exports and current validation evidence live in `build/`. The FDM printability checks are separate from fidelity to the original thin aluminium part. The nominal model has not been physically fitted to a Palm V.
