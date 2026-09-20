# nurb models

Personal parametric CAD models built with [nurb](https://github.com/Shpigford/nurb).

The repository is itself a nurb project: each Python file in `parts/` is an editable model, its Markdown card records reconstruction context, `scans/` contains comparison targets, and `references/` contains source CAD used directly by a model.

## Models

| Part | Description | Reference |
| --- | --- | --- |
| `maixcam2` | MaixCAM2 enclosure, radiator grille, camera stack, and PMOD sockets | `scans/Maixcam2.stl` |
| `utility_blade_holder` | Parametric EDC utility blade holder reconstruction | `scans/Utility_Blade_Holder.STL` |

## Use

```bash
nurb dev
nurb build maixcam2
nurb build utility_blade_holder
```

Generated exports and renders belong in `build/` and are intentionally not committed.
