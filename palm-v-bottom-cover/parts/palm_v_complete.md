# Palm V complete exterior reconstruction

```toml
target = { file = "scans/palm-v-rough-observed.ply.gz", units = "mm", tolerance_mm = 0.5, transform = [-0.10922572644686877, 0.6454672384636836, -0.7559376857600234, 0.6376355473739272, 0.994016907224094, 0.0706513663750424, -0.08329929520702148, -0.24791964318279427, -0.00035893564991422314, -0.7605132664848164, -0.6493222949089253, 3.870885865838079, 0.0, 0.0, 0.0, 1.0] }
```

## What it is

This reconstruction uses the supplied scan as one assembled PDA. The STL supplied on 2026-09-30 is the same original whole-device geometry already preserved in `scans/palm-v-rough-observed.ply.gz`; it is not a newly scanned bottom cover. The fixed scan datum is retained. All long side rails, lower flares, metal main forms, application keys and docking features use exact left/right symmetry. The measured power and contrast controls and existing reset opening remain intentionally asymmetric.

## Design notes

The accurate prior smooth front and rear metal masters are retained. A new whole-device frame replaces the earlier partly disassembled chassis representation in this assembly only. Its external C-shaped stylus/accessory channels are fitted from true whole-scan horizontal sections with averaged left/right crossings and straightened long rails. The channels are deliberately recessed around X=±35.7 mm between the rolled outer lips near X=±38.7 mm; smoothing does not fill them. `references/complete-frame-fit.json` records the fitted outline controls. Hidden frame geometry is a simple support ring, not a reconstruction of the electronics or attachment system.

The previous rear dock void is closed by a curved housing, ten recessed contact lanes at 2 mm pitch, their separate metal contact surfaces, and paired deep latch recesses that cut through both the dock housing and frame to measured Z=-2.6 mm floors. The curved rear dock face follows measured sections, including its rapid roll into the lower end. Paired rear locating nubs are modeled without assigning an unsupported screw function. The upper power and contrast controls are separate named solids; the front metal includes their openings. The scroll rocker has a smooth longitudinal crown fitted from the whole-scan center section, replacing the earlier straight tilted top; its opening follows the corrected Y=-53.2 to -38.1 mm outline and has an opaque nominal backing. An opaque display edge seat closes the gap behind the measured glass perimeter and stays below the metal bezel. Shallow seats behind the application buttons and curved scroll clearance close unintended views into the empty surrogate frame; these are nominal exterior closures, not inferred switch mechanisms or display stack dimensions. The scan supports the display opening and flat display plane, but does not recover LCD pixels, printed Graffiti icons, logos, fine lettering, materials or exact hidden stack dimensions. Component colors communicate plausible material groups only.

The retained `palm_v` assembly and its separate part sources remain available as historical design work. Its current detailed intermediate-frame rebuild fails an internal seating check, so its older exported assembly is not a current deliverable. This complete model is the primary whole-device exterior, with separately editable components. It is not a replacement-part manufacturing drawing. `build/palm_v_complete-validation.json` binds reopened STEP, GLB and STL checks to artifact and input hashes. The STL preserves separate exterior component shells and is not a certified single fused printable body. `build/palm_v_complete-comparison.json` records the independently sampled exterior comparison when present.

Rebuild with `python references/export_complete.py`. Regenerate the frame fit with `python references/fit_complete_frame.py`; it reads the preserved source mesh and saved rigid datum.

## Don't

Do not fill the paired stylus/accessory channels, mirror the intentionally asymmetric power, contrast or reset controls, use stale exports of the historical `palm_v` assembly as this revision, or infer physical internal fit from the nominal exterior support geometry.

## Changelog

2026-09-30: Re-audited the supplied STL as a complete PDA, retained the independently accurate metal masters, rebuilt smooth symmetric side channels from whole-device sections, restored the rear connector and upper controls, closed the display perimeter, and added independent CAD and mesh export validation.
