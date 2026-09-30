# Palm V nominal exterior assembly

```toml
target = { file = "scans/palm-v-rough-observed.ply.gz", units = "mm", tolerance_mm = 0.5, transform = [-0.10922572644686877, 0.6454672384636836, -0.7559376857600234, 0.6376355473739272, 0.994016907224094, 0.0706513663750424, -0.08329929520702148, -0.24791964318279427, -0.00035893564991422314, -0.7605132664848164, -0.6493222949089253, 3.870885865838079, 0.0, 0.0, 0.0, 1.0] }
```

A clean nominal reconstruction inferred from the supplied rough assembled scan and separate rear/frame scans. Main forms are bilaterally symmetric; the rear Reset hole remains intentionally offset. This is not recovered OEM drawing data.

The front and rear aluminium shapes are independently fitted. The front has a smooth cubic skin, a measured curved-bottom display opening, four round application keys, and a central hourglass scroll control. Named components can be hidden or isolated without rebuilding the model.

The rear pose was fitted using its original observed exterior, then applied unchanged to the nominal straightened cover. `references/palm-assembly-poses.json` records that rigid placement and residuals. The chassis pose is fixed to the shared rear-interface datum. Its rear seating bands derive from the nominal inner metal surface, independently of the front curve. The front and rear sheet gauges are passed to the matching chassis interfaces together. Contact and interference results are recorded with the exported geometry.

Hidden front sheet gauge, button underside geometry, display stack thickness, internal attachments and electronics are not established by this exterior scan. Glue, scan noise, text relief and accidental distortions are omitted. Do not treat this assembly as production fit validation.
