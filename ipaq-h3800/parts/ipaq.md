# iPAQ assembly

```toml
[variants.exploded.params]
exploded = 20.0
```

## What it is

Front and back are separate editable CAD solids in one registered assembly. The board and its processor, memory, card socket, navigation shield and connectors use simple rectangular envelopes. Display, the curved speaker cap, a dished oval navigation control and five domed buttons remain separate components.

## Design notes

The display plane is Z=0. The case seam is Z=-4.3 and the nominal PCB top is Z=-7.5. Rear placement comes from four visible bore centres and exposed outer rims; see references/registration.json. The complete front is divided at the photographed speaker-cap boundary for the assembly. The default is assembled. The exploded variant spreads the two shells and display for inspection.

## Don't

Do not align the parts by independent scan bounding-box centres or use the PCB underside as the case seam. The component blocks are approximate; hidden mounting details and material thicknesses require physical confirmation for manufacturing.


## Mating revision

The shells share a complementary rear-cover perimeter, with continuous front end returns and a 0.2 mm nominal pocket clearance. The navigation shield remains a generic rectangle, reduced to 4.2 mm depth to clear that return. The independent seam and interference reports are in the report produced by references/validate_assembly.py. Physical fit remains unverified.
