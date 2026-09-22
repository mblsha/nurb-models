# Palm V cover reconstruction audit

The first reconstruction is rejected. It built as a valid solid, but that did not establish that it represented the scanned bent aluminium cover. The previous claim that the model was complete was incorrect.

## What was sound

- The original THREE group registration was retained after the user clarified that it was already aligned. The later bilateral coordinate transform was recorded separately.
- The observed reference retained real, asymmetric measurements rather than replacing them with a mirrored synthetic cloud. Source hashes and deterministic voxel selection provide useful provenance.
- The Reset opening was added after the symmetric blank. Independent checks tested sampled reflection and confirmed the final removal was confined to that opening.
- STEP and 3MF round-trip checks established useful basic export validity.

## Confirmed failures

1. The raised central form was built by fusing an ellipsoid onto the sheet without a corresponding inner surface. Independent OCCT line intersections found 0.919 mm of metal at X=0, Y=18 instead of the nominal 0.400 mm. At Y=14.5 the construction has two separate material intervals, with a 0.159 mm air gap between them. This is not a formed sheet.
2. The broad surface is a cylinder extruded along Y. Its height is independent of Y, although measured sections show longitudinal curvature. Its source comment incorrectly calls it a sphere.
3. The perimeter uses square extrusion/cut corners and a constant bottom plane. This does not reproduce curved bends or the variable edge geometry visible in the other scan groups.
4. Both side groups were excluded wholesale because they also contained glue and fixtures. That discarded useful metal observations along with contamination. The exterior-only fit could not validate the returned edges or inner surface.
5. The archive contains 24 original triangle meshes with 10,800,890 faces. MAF's prepared cloud export removes that connectivity. Describing the original source as an unorganized point-only cloud was incorrect; an observed mesh could have been retained without inventing triangles or filling holes.
6. The central rectangular through-slot visible in both exterior and interior source photos was omitted.
7. The validator checked topology, sampled symmetry, Reset-only removal, and export round trips, but not thickness, bend shape, curve fidelity, or deviation against observations. Its unqualified `accepted: true` therefore overstated what it proved.
8. The raw STL was not watertight. Accepting its largest component did not make the delivered file clean.
9. The README still said CAD had not been created. Regional fit values were reported in conversation without a saved, reproducible comparison script and region definitions.
10. A failed loopback request inside the sandbox was mistaken for stopped servers. Elevated verification later showed the original servers were still running. Server state should be verified before announcing a restart.
11. The claimed symmetry did not survive independent interior probes. In the reopened STEP, X=+35,Y=40 contains metal at Z=-1.10..-0.70 as well as Z=-0.527..-0.127; X=-35,Y=40 only contains the latter interval. The same mismatch occurs at Y=52. A reflected surface probe is 0.573 mm from the opposite surface. The sparse boundary/face test missed this asymmetry, so the old assertion of an exactly bilateral formed blank was also incorrect.
12. The return was formed on the wrong side of the exterior. Original side observations put the interior and rising rims toward +Z, with rim observations up to 4.88 mm. The old model built a skirt toward -Z and had a total height of only 1.72 mm.
13. The previous 0.40 ±0.10 mm thickness statement was not adequately measured. Clean paired observations from independent groups suggest separation near 0.65–0.70 mm, with spatial variation from residual registration, adhesive, and measurement error. A nominal gauge must remain provisional until verified physically.

## Recommendations for subsequent reconstructions

| Priority | Change | Required evidence |
| --- | --- | --- |
| 1 | Inspect all source groups and retain source mesh connectivity before choosing a comparison representation. | Source inventory, transform chain, original triangle provenance, and explicit contamination masks. |
| 1 | Establish physical sides, symmetry plane, and longitudinal/transverse profiles before choosing CAD primitives. | Annotated source views and measured section plots with the proposed surface overlaid. |
| 1 | Build a smooth curved sheet and offset its entire surface along normals. | Gauge measurements through broad skin, raised form, and bends; no unintended doubled layers or gaps. |
| 1 | Use clean portions of side scans to constrain bends instead of dropping complete groups. | Local masks, section coverage, and uncertainty by region. |
| 1 | Account explicitly for visible functional features, including the central slot and Reset hole. | A feature checklist tied to source views and boundary measurements. |
| 1 | Keep topology, symmetry, reconstruction fidelity, export quality, and physical fit as separate verdicts. | A saved report that names passing, failing, uncertain, and untested checks separately. |
| 2 | Preserve source/model hashes, units, sample seeds, region masks, and thresholds with fit reports. | Reproducible commands and numeric output, including worst regions and source coverage. |
| 2 | Review top, oblique, edge, underside, and section views before delivery. | Saved comparison images with a shared camera and scale. |
| 2 | Validate complete exported artifacts, not only their largest connected components. | No degenerate triangles or unexpected components; valid reopened STEP and manifold closed print meshes. |
| 2 | Reconcile README, measurements, part card, and report before claiming completion. | One consistent status with unresolved assumptions stated plainly. |

The replacement must be evaluated on its actual measured fit and sheet construction. Passing the rejected version's validator is not an acceptance criterion.
