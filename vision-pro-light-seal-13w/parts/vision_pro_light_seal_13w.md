# Vision Pro Light Seal 13W

A fresh reconstruction of the external shell using two smooth mating loops and a single broad intermediate shape. The part is one connected solid with four continuous surfaces. The black nose cloth and interior details are outside its scope.

```toml
target = { file = "scans/vision-pro-light-seal-13w-reference.glb", units = "mm", tolerance_mm = 1.0, transform = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0] }
```

## Geometry

The headset and cushion interfaces are closed periodic splines through sparse regularized scan landmarks. A smooth outside surface joins the interfaces; a plain inside surface supplies the wall. The two integral end faces provide the mating rims. The broad hard nose saddle remains, while the cloth that crosses the opening is omitted.

## Evidence and limitations

The observable mating rims are fitted to the supplied textured scan in its established datum. The headset interface near the nose is partly obscured by cloth; this section uses a broad smooth interpolation. The scan establishes the overall geometry, not a guaranteed physical fit tolerance.

## Dimensions and verification

The default shell is approximately 161.2 × 95.7 × 85.5 mm in the scan datum. It is one valid solid with four B-spline faces, each C2-continuous around the perimeter. Nominal middle-wall thickness is 1.8 mm, with 3.2 mm transverse mating rims. STEP reopens as one valid solid; STL and 3MF each reopen as one watertight connected mesh. The exports use the canonical `vision_pro_light_seal_13w` name. Adaptive OCCT volume is 37,452.3 mm³; the kernel's default non-adaptive mass calculation overestimates these broad spline surfaces.

Observed headset-rim centerline deviation has a 0.30 mm median and 0.89 mm 95th percentile; 97.5% lies within 1 mm of the scan. Cushion-rim centerline deviation has a 0.28 mm median and 1.22 mm 95th percentile; 91.7% lies within 1 mm. These are centerline-to-scan measurements, not a proof of mating-face tolerance or physical fit. The rear nose zone at |X| < 30 mm and Y > 0 is reported separately because cloth obscures the rigid interface: its regularized curve reaches 6.66 mm from the visible scan. This uncertain portion needs a physical test fit rather than following the cloth surface.

`references/validate_reconstruction.py` reproduces the export checks and 1,000 samples along each mating loop. It measures exact closest points among 64 nearby triangles and checks eight samples per loop against exhaustive triangle search, with zero observed acceleration error. Detailed evidence is in `measurements.toml`; fresh validation writes `build/reconstruction_validation.json`.

## Source and texture

The original `references/source/Light seal.ply` and `Light seal.png` remain byte-for-byte preserved. `references/source/convert_reference.py` retains the original UV atlas, removes only detached scan specks, and embeds the unchanged texture into `scans/vision-pro-light-seal-13w-reference.glb`. Both scan and reconstruction use the same U/V/W datum: U runs left to right, V follows the face opening, and W runs from headset toward cushion. The card explicitly preserves identity alignment.

## Printing

The model remains in reference alignment for inspection. Its curved lower edge and unsupported surfaces require a chosen print orientation and supports. The default wall passes the current thin-wall check; the orientation-related overhang and bed-stability findings remain. Black nose-guard cloth, internal ribs, magnets, recess details, texture relief, and cosmetic seams are intentionally absent.
