# nurb models

Personal parametric CAD models built with [nurb](https://github.com/Shpigford/nurb).

This repository contains independent nurb projects. Open a project subdirectory in the nurb desktop app, or run nurb commands from that subdirectory. The repository root is not a nurb project.

## Projects

| Project | Description | Reference |
| --- | --- | --- |
| [maixcam2](maixcam2/) | MaixCAM2 enclosure, radiator grille, camera stack, and PMOD sockets | [Binary PLY reference](maixcam2/scans/Maixcam2.ply) and [camera adapter STEP](maixcam2/references/maixcam2-camera-mount.step) |
| [neewer-gm-mp2](neewer-gm-mp2/) | Neewer GM-MP2 macro focusing rail, carriage, quarter-turn Arca mount, retractable feet, and focus controls | [Compressed binary PLY reference](neewer-gm-mp2/scans/neewer-macro-slide-GM-MP2.ply.gz) and [exact outer focus sleeve STEP](neewer-gm-mp2/references/neewer-outer-focus-sleeve.step) |
| [utility-blade-holder](utility-blade-holder/) | Parametric EDC utility blade holder reconstruction | [Source STL](utility-blade-holder/scans/Utility_Blade_Holder.STL), from [Thingiverse 3713857](https://www.thingiverse.com/thing:3713857) |
| [vision-pro-light-seal-13w](vision-pro-light-seal-13w/) | Symmetric Vision Pro Light Seal 13W shell with a small retaining lip on the narrow Vision Pro rim and eight cushion attachment recesses | [Textured reference GLB](vision-pro-light-seal-13w/scans/vision-pro-light-seal-13w-reference.glb) and original PLY/PNG under `references/source/` |

Each project contains its own `parts/` Python models and Markdown cards, plus `scans/` comparison targets. Target paths in the cards are relative to that project's root.

## Reference mesh storage

Convert imported STL reference meshes to geometry-only binary little-endian PLY before their first commit. Binary PLY shares vertices instead of repeating three vertices per triangle, so it is substantially smaller while preserving the triangle geometry exactly. Set `units = "mm"` explicitly in the part card because PLY does not declare units, and omit vertex colors and stored normals because nurb recomputes what comparison and rendering need.

Nurb opens `.ply.gz` comparison targets directly, so gzip large binary PLY references when it materially reduces their committed size. The decompressed PLY remains subject to nurb's safety limit.

Textured PLY scans retain their source PLY and texture image under `references/source/`. A reproducible converter creates a GLB comparison target with the original texture embedded and UV seams preserved; geometry-only PLY conversion would lose that reference appearance.

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

Or start the Neewer GM-MP2 project:

```bash
cd neewer-gm-mp2
nurb dev
```

Or start the Vision Pro Light Seal project:

```bash
cd vision-pro-light-seal-13w
nurb dev
```

Within a project, `nurb build` builds all its parts, `nurb check` reports findings, and `nurb compare <main-part>` compares its main model with the stored reference.

Generated exports and renders belong in each project's `build/` directory and are intentionally not committed. The source meshes remain alongside their projects so comparisons are reproducible.
