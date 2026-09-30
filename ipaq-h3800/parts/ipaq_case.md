# iPAQ front, back and PCB

```toml
[variants.exploded.params]
exploded = 20.0
```

## What it is

A combined three-part mechanical assembly: the complete front shell, the asymmetric back cover and a generic PCB. The default pose is assembled. The exploded variant moves only the shells along Z and retains all mounting-axis alignment. The separate `ipaq` assembly adds the display, controls and simple electronic component envelopes.

## Design notes

All three parts use the same four registered mounting centres from `case_profiles.mounted_holes()`. No additional XY placement or independent centering occurs in this assembly. The front posts seat on the PCB top at Z=-7.5 mm; the PCB underside at Z=-8.5 mm has a nominal 0.1 mm clearance above the rear mounting lands. The ordinary shell seam has a nominal 0.2 mm receiver allowance. The one-sided flared shoulder uses a curved front underlap with nominal 0.25 mm relief.

## Don't

Do not align the components by their bounding boxes, mirror the back shoulder, or confuse the exploded inspection pose with the assembled fit. PCB geometry and electronics are simplified. CAD alignment is checked independently of the noisy scan registration; physical fit and absolute scan scale remain uncalibrated.
