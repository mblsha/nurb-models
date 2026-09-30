# US Robotics Palm Pilot Professional

Editable exterior CAD reconstructed from the supplied textured body and stylus scans. It includes the asymmetric case, curved controls, paired docking sockets, two sliding rear covers, and a fitted stylus with eight measured grooves. Concealed seats, cavity clearances and blind socket floors are nominal; this is not a physically verified replacement enclosure.

## Open and build

Install the pinned public nurb revision in [requirements.txt](requirements.txt), which provides the named-component and clearance APIs used by the complete assembly. PyPI nurb 0.26.0 can build the four standalone parts but lacks those assembly APIs. Open this directory in the nurb desktop app, run `nurb dev`, or launch `viewer.command`. Select `palm_pilot_professional` for the complete seventeen-component assembly. The `covers_open` and `covers_removed` variants move both rear covers; `withdrawn` slides the stylus out by 30 mm. The lower battery cover slides left. The broad upper memory cover slides toward the top and carries its upper-left foot.

```bash
python -m pip install -r requirements.txt
nurb build
nurb export palm_pilot_professional --formats step stl glb
python export_model.py
python export_model.py --variant covers_open
python export_model.py --variant covers_removed
python export_model.py --variant withdrawn
```

Run Python from the environment containing nurb. The shared geometry is in `palm_pilot_geometry.py`; the five models and cards are in `parts/`. Normal CLI/viewer downloads contain four independently buildable parts: `palm_pilot_body` (fixed exterior and controls), `palm_pilot_battery_cover`, `palm_pilot_memory_cover` (including its foot), and `palm_pilot_stylus`. Both covers are single connected solids and are excluded from the fixed body export.

`export_model.py` writes the complete named assembly STEP and combined STL/GLB. It unions contacting body material, then places the separately validated stylus mesh using double-precision coordinates. The combined STL uses full-precision ASCII coordinates to preserve small valid triangles. STEP retains named editable components. Generated artifacts and their export metadata are written under `build/` and are intentionally not committed.

## References and limits

Original textured PLY/PNG assets and self-contained reference GLBs are under `scans/`. Their import metadata preserves filenames, units and source hashes. Original upload ZIPs and superseded comparison meshes remain in the local development archive; the published project does not depend on them. Card paths and fixed registration matrices are relative to this project. No generated file is required to build the CAD.

The stylus comparison target excludes Blu Tack while restoring genuine shaft faces that the first mask removed. Its exact face-selection provenance and fitted datum are recorded in [stylus-fit.json](references/stylus-fit.json) and [stylus-reference-mask.json](references/stylus-reference-mask.json). The round shaft through the obscured interval is a reconstruction.

[Source and validation notes](references/MEASUREMENTS.md) distinguish observed exterior geometry from nominal hidden construction and summarize the completed source comparisons, symmetry, interference and saved-mesh checks. Printed markings remain texture rather than invented engraved geometry. No batteries, electronics, unseen rails, snap hooks or switch mechanism are modeled.
