from nurb import *

from system import at, rounded_prism


@part
def pmod_socket(
    pitch=2.54,
    columns=6,
    rows=2,
    housing_height=2.4,
    entrance_width=1.05,
    draft=False,
):
    """A standard 2 x 6 female PMOD socket centered on the origin.

    pitch: center spacing between adjacent contacts
    columns: number of contacts along X
    rows: number of contacts along Y
    housing_height: socket body height above its seating plane
    entrance_width: square pin entrance width
    """
    housing_width = columns * pitch
    housing_depth = rows * pitch
    housing = rounded_prism(
        housing_width,
        housing_depth,
        0.25,
        housing_height,
        -housing_width / 2.0,
        -housing_depth / 2.0,
    )
    entrances = []
    for column in range(columns):
        for row in range(rows):
            x = (column - (columns - 1) / 2.0) * pitch
            y = (row - (rows - 1) / 2.0) * pitch
            opening = RectangleRounded(
                entrance_width,
                entrance_width,
                0.12,
                align=(Align.CENTER, Align.CENTER),
            )
            entrances.append(extrude(at(opening, x, y, housing_height - 1.25), amount=1.35))
    return housing - Compound(entrances)
