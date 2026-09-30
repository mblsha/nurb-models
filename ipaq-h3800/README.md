# iPAQ H3800 case assembly

The main model is `ipaq_case`: the complete front shell, the asymmetric rear cover and a generic PCB in one assembly. All three use the same four mounting axes. The back's one-sided flared lip is retained, and the front curls underneath it. The repaired navigation boundary stays flat. Select the exploded variant to inspect the interior without changing the XY alignment.

The additional `ipaq` model includes the display, speaker-cap region, controls and simple rectangular electronic component envelopes. Individual `front`, `back` and `pcb` models remain editable. Dimensions follow the supplied scans, with photographs used to interpret the H3800 family features. The exact SKU is unconfirmed.

## Open the combined model

Open this directory in the nurb desktop app and select `ipaq_case`, or run:

```sh
nurb dev
```

Select `ipaq_case` in the viewer. The `exploded` variant separates the shells by 20 mm. The default pose is assembled. Component visibility and the section control let you inspect the screw alignment and the curved side joint. No desktop or engine changes are required.

## Alignment and validation

The display plane is Z=0. The front posts seat on the PCB top at Z=-7.5 mm. The 1 mm board has a nominal 0.1 mm clearance above the rear mounting lands. The ordinary rear-cover receiver has 0.2 mm nominal lateral clearance; the asymmetric shoulder uses 0.25 mm nominal underside relief. The scan's four-bore registration fixes the back at X=4.10 mm, Y=0.45 mm and yaw=-0.308 degrees. No independent centering or extra XY placement is applied in the combined assembly.

Run the verification and export script from this directory:

```sh
python references/validate_assembly.py
```

Use the Python environment that contains nurb, build123d and trimesh. The script builds all three parts, intersects the actual bore walls at two heights, checks the mounting-land gaps, checks every pair for solid interference, samples the shell seam and verifies the exported STEP again. Deliberately translating the PCB by 0.25 mm in X or Z must fail. Checks remain active under `python -O`.

The script writes `build/ipaq-case.step`, with three named CAD solids, `build/ipaq-case.glb`, individual STEP files and `build/assembly-validation.json`. STEP uses millimetres; GLB uses standard glTF metres. Generated exports and renders are ignored by Git.

For separate CAD render sheets:

```sh
nurb render ipaq_case --sheet
nurb render front --sheet
nurb render back --sheet
```

## Sources and limits

The reconstruction used separate front and back scans. The scan assets, textures and user annotation remain in the local reconstruction project and are not included in this public repository. Every CAD part builds independently of those inputs. Public part cards omit local scan-target blocks so opening a fresh checkout does not require missing files.

The annotations and scans establish that the raised speaker-side corner is a real asymmetric mating feature. It must not be mirrored or flattened. `case_profiles.py` owns the shared shoulder geometry, cover outline and fastener registration. Hidden ribs, clips, thicknesses and mating details are reconstructed. The board and electronic components are mechanical envelopes, not an electrical design.

The geometric checks verify CAD alignment, not manufactured fit. The source scale is provisionally millimetres without an external calibration object, and the scan bore registration has residuals of approximately 0.24 to 0.35 mm. Printed or machined replacement parts still require physical checking. Public photo references and the fixed assembly registration are recorded in `references/photo-sources.json` and `references/registration.json`.
