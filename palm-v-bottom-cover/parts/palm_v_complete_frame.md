# Smooth whole-device Palm V frame

```toml
target = { file = "scans/palm-v-rough-observed.ply.gz", units = "mm", tolerance_mm = 0.5, transform = [-0.10922572644686877, 0.6454672384636836, -0.7559376857600234, 0.6376355473739272, 0.994016907224094, 0.0706513663750424, -0.08329929520702148, -0.24791964318279427, -0.00035893564991422314, -0.7605132664848164, -0.6493222949089253, 3.870885865838079, 0.0, 0.0, 0.0, 1.0] }
```

## What it is

A single valid exterior support ring derived from the assembled PDA scan, with exactly mirrored cubic side contours and smooth section lofting. The paired side recesses are stylus/accessory channels visible in the whole scan. Only their broad external form and lower flare are represented; the unseen interior is intentionally simple. This frame belongs to `palm_v_complete` and does not replace the earlier separately scanned intermediate chassis or establish a production mating interface.

## Design notes

The long side runs are exact lines at every fitted depth, with tangent-constrained cubic end blends. Bilateral mirror construction is checked independently on the exported BRep.

## Don't

Do not flatten the recessed channels, import scan noise into the straight rails, or treat this exterior ring as a reconstruction of hidden electronics and attachments.

## Changelog

2026-09-30: Added the smooth whole-device frame fitted from the original assembled scan.
