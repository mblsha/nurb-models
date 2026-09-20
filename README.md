# nurb models

Personal parametric CAD models built with [nurb](https://github.com/Shpigford/nurb).

This repository contains two independent nurb projects. Open the `maixcam2/` or `utility-blade-holder/` subdirectory in the nurb desktop app, or run nurb commands from that subdirectory. The repository root is not a nurb project.

## Projects

| Project | Description | Reference |
| --- | --- | --- |
| [maixcam2](maixcam2/) | MaixCAM2 enclosure, radiator grille, camera stack, and PMOD sockets | [Source STL](maixcam2/scans/Maixcam2.stl) and [camera adapter STEP](maixcam2/references/maixcam2-camera-mount.step) |
| [utility-blade-holder](utility-blade-holder/) | Parametric EDC utility blade holder reconstruction | [Source STL](utility-blade-holder/scans/Utility_Blade_Holder.STL), from [Thingiverse 3713857](https://www.thingiverse.com/thing:3713857) |

Each project contains its own `parts/` Python models and Markdown cards, plus `scans/` comparison targets. Target paths in the cards are relative to that project's root.

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
