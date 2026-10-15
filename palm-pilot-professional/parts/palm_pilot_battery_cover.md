# Palm Pilot Battery cover

## What it is

The lower rear cover slides toward the left edge (negative X) and includes its observed rolled side return and shallow thumb dish. The fixed body export excludes this cover. The main assembly provides closed, partly open and fully removed configurations.

## Design notes

The exterior footprint comes from the supplied closed scan and original-device removal evidence. Concealed backing and slide-seat clearances are nominal; no unobserved guide rails or snap hooks are modeled. overall_scale preserves the assembly proportions. See the [source and validation notes](../references/MEASUREMENTS.md) for measured boundaries and evidence.

The flat exterior and backing planes use the same rigid body datum as the display and both casing halves. Outward motion is derived from that frame rather than an independently fitted rear slope. The observed curved return/bulge remains a curved feature. See `checks/check_parallel_planes.py` for the repeatable actual-face constraint check.

## Validation

This export must remain one valid connected solid with a watertight serialized mesh. Its native motion is checked against the fixed case and the other seated cover through intermediate and fully removed poses. The published notes summarize the completed checks; generated meshes and development audit artifacts remain local.
