# Palm V front aluminium cover

```toml
target = { file = "scans/palm-v-rough-observed.ply.gz", units = "mm", tolerance_mm = 0.5, transform = [-0.10922572644686877, 0.6454672384636836, -0.7559376857600234, 0.6376355473739272, 0.994016907224094, 0.0706513663750424, -0.08329929520702148, -0.24791964318279427, -0.00035893564991422314, -0.7605132664848164, -0.6493222949089253, 3.870885865838079, 0.0, 0.0, 0.0, 1.0] }
```

A smooth exactly mirrored front shell fitted independently from the rear cover, using the rough assembled scan. Symmetric XYZ cubic surface coefficients, including unrolled inward-curving rim sections, and fit masks are in `references/front-fit.json`. The rear cover is not used to generate the front shape.

The displayed front seam is provisionally placed at the fitted 1.5 mm depth contour. Sheet gauge defaults to 0.65 mm until a separate front scan or physical measurement establishes it. The visible curved-bottom screen opening, four application-button openings, and hourglass scroll opening are included. Tiny lettering, glue and hidden attachments are omitted.

The independent reopened STEP checks verify a single solid, 0.65 mm normal gauge, bilateral symmetry, and all visible openings. `build/front-validation.json` and `build/front-interface-checks.json` record the artifact hashes and insert clearances. `build/front-region-comparison.json` keeps unambiguous front metal separate from low-depth observations that may belong to the black chassis. The front cut-edge and scroll opening remain provisional until the separate front scan is available.

Reproduce the fit from the preserved original PLY and fixed alignment with `python references/fit_front.py`. Regional comparison uses `python references/compare_front_regions.py`; it requires no temporary prepared cloud. Run `python references/validate_front.py`, `python references/check_front_interfaces.py`, and `python references/export_front_components.py` after rebuilding the component STEP files.
