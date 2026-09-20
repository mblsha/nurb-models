# nurb models

Personal parametric CAD models built with [nurb](https://github.com/Shpigford/nurb).

This repository contains two independent nurb projects. Open the `maixcam2/` or `utility-blade-holder/` subdirectory in the nurb desktop app, or run nurb commands from that subdirectory. The repository root is not a nurb project.

## Projects

| Project | Description | Reference |
| --- | --- | --- |
| [maixcam2](maixcam2/) | MaixCAM2 enclosure, radiator grille, camera stack, and PMOD sockets | [Binary PLY reference](maixcam2/scans/Maixcam2.ply) and [camera adapter STEP](maixcam2/references/maixcam2-camera-mount.step) |
| [utility-blade-holder](utility-blade-holder/) | Parametric EDC utility blade holder reconstruction | [Source STL](utility-blade-holder/scans/Utility_Blade_Holder.STL), from [Thingiverse 3713857](https://www.thingiverse.com/thing:3713857) |

Each project contains its own `parts/` Python models and Markdown cards, plus `scans/` comparison targets. Target paths in the cards are relative to that project's root.

## Reference mesh storage

Convert imported STL reference meshes to geometry-only binary little-endian PLY before their first commit. Binary PLY shares vertices instead of repeating three vertices per triangle, so it is substantially smaller while preserving the triangle geometry exactly. Set `units = "mm"` explicitly in the part card because PLY does not declare units, and omit vertex colors and stored normals because nurb recomputes what comparison and rendering need.

Gzip can reduce a binary PLY further for archival storage, but nurb does not currently open `.ply.gz` directly. Keep the active comparison target as an uncompressed `.ply`; use a gzipped copy only outside the active project or as a separately downloadable archive.

The `maixcam2` assembly uses the independently buildable `maixcam2_body`, `pmod_socket`, `maixcam2_camera_base`, `maixcam2_camera_mount`, and `maixcam2_lens` parts. Their shared helpers live in `maixcam2/system.py`, and the camera adapter imports the STEP file from that project's `references/` directory.

## Use

From the repository root, start the MaixCAM2 project:

```bash
cd maixcam2
nurb dev
```

Or start the blade holder project from the repository root:

```bash
cd utility-blade-holder
nurb dev
```

Within either project, `nurb build` builds all its parts, `nurb check` reports printability findings, and `nurb compare maixcam2` or `nurb compare utility_blade_holder` compares the main model with its stored reference.

Generated exports and renders belong in each project's `build/` directory and are intentionally not committed. The source meshes remain alongside their projects so comparisons are reproducible.
