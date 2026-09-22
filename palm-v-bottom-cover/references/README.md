# Palm V bottom-cover references

The archive contains 24 triangulated scans. The THREE hierarchy already aligns their groups; that registration is retained. The recorded bilateral transform changes only the common coordinate frame: X=0 is the upright cover's long symmetry plane, Y follows its length, and +Z points toward the interior and raised rims. The model must retain the different top and notched bottom ends. The offset Reset opening is an intentional left/right asymmetry.

## Observed point cloud

`../scans/palm-v-bottom-cover-back-observed.ply.gz` contains 495,454 measured exterior samples from group 1 (`back`). Its deterministic 0.17 mm voxel reduction keeps the first original row per occupied voxel, including measured coordinates, transformed normals, RGB, and source identifiers. No points are averaged, mirrored, or synthesized. `import-alignment.json` records its source hashes, transform, and bounds. Reflection residuals in that file describe alignment evidence, not CAD accuracy.

MAF's prepared group PLY is vertex-only because cloud preparation discards triangle connectivity. The original archive is not point-only. The earlier claim that a comparison mesh would require invented connectivity was incorrect.

## Original observed triangles

`../scans/palm-v-bottom-cover-comparison-triangles.ply.gz` restores the original face connectivity. It combines complete exterior scan 17 with spatially selected return observations from side scans 1 and 10, for 376,165 vertices and 740,708 triangles. Source vertex and face indices are retained. Every vertex is an original measured vertex under the recorded rigid transform; every face is an original observed triangle. No remeshing, filling, closure, or CAD-derived surface is inserted.

`original-triangle-provenance.json` records the exact transforms, scan selection, side-region mask, artifact hashes, and full archive counts. The compact comparison set avoids redundant overlapping observations from all 24 scans. The generator can reproduce the complete back and selected side-region meshes too, but those large intermediate outputs are not packaged in this project.

The side mask excludes most fixtures but is not a semantic glue classifier. Residual adhesive, imperfect registration, open scan boundaries, and overlapping observations remain limitations. Use local section evidence to distinguish the metal from contamination. Do not interpret a global nearest-surface statistic as proof of gauge or fit.

Reproduce observed meshes with Python and NumPy:

```bash
python3 references/import_observed_mesh.py /path/to/project.zip --output-dir /path/to/generated-meshes
```

Reproduce the point cloud from the frozen MAF prepared group:

```bash
python3 references/generate_reference.py \
  --source /path/to/maf-library/prepared/f6722ad291d3c3a3c1a7806de1b2234bea7e78cd5361351b62bcfa0133a0b7af/group-1-0ca4f855c09c/full.ply \
  --merge-manifest /path/to/maf-library/exports/8c862af92e424c3aa40b091fe5bbbf30/merge.json
```

Both paths preserve the supplied relative registration. The symmetry requirement belongs to the reconstructed CAD; observations remain asymmetric so they can serve as independent evidence.

## Review evidence

`observed-sections.png` compares source groups in the same frame. It exposes the curved end and side returns omitted from the first reconstruction. `audit-v1.md` records that reconstruction's confirmed defects and the process changes required for its replacement.
