from nurb import *

from system import at, cylinder, rounded_prism


@part
def maixcam2_body(
    body_width=66.5,
    body_depth=50.2,
    body_height=20.46,
    corner_radius=6.0,
    grille_rib_height=0.9,
    camera_center_x=33.5,
    camera_center_y=40.0,
    draft=False,
):
    """The enclosure shell, top grille, bosses, buttons, and connector openings."""
    if corner_radius <= 0.0:
        reject("corner_radius must be greater than zero", param="corner_radius")
    if grille_rib_height <= 0.0:
        reject("grille_rib_height must be greater than zero", param="grille_rib_height")

    body = rounded_prism(body_width, body_depth, corner_radius, body_height)
    ribs = []
    for row in range(7):
        center_y = 10.8 + 3.14 * row
        ribs.append(
            loft(
                [
                    at(SlotOverall(59.8, 1.9), 33.48, center_y, body_height - 0.02),
                    at(SlotOverall(59.8, 1.4), 33.48, center_y, body_height + 0.65 * grille_rib_height),
                    at(SlotOverall(59.8, 0.5), 33.48, center_y, body_height + grille_rib_height),
                ],
                ruled=False,
            )
        )
    body += Compound(ribs)

    adapter_rib_clearance = at(
        Box(28.1, 0.2, grille_rib_height + 0.1, align=(Align.MIN, Align.MIN, Align.MIN)),
        camera_center_x - 14.05,
        camera_center_y - 9.55,
        body_height - 0.01,
    )
    body -= adapter_rib_clearance

    pmod_centers = ((11.35, 38.65), (55.26, 38.68))
    body -= Compound(
        [
            rounded_prism(15.9, 5.8, 0.5, 2.7, x - 7.95, y - 2.9, body_height - 2.5)
            for x, y in pmod_centers
        ]
    )
    reliefs = []
    for x, y in (
        (4.2, 35.6),
        (4.2, 41.9),
        (18.2, 35.7),
        (18.2, 41.8),
        (48.3, 35.6),
        (48.4, 41.8),
        (62.3, 35.6),
        (62.4, 41.9),
    ):
        reliefs.append(extrude(at(SlotOverall(1.8, 1.1), x, y, body_height - 0.5), amount=1.0))
    body -= Compound(reliefs)

    boss_centers = ((5.3, 5.1), (61.0, 5.0), (5.4, 45.4), (61.2, 45.25))
    bosses = []
    screw_holes = []
    for x, y in boss_centers:
        bosses.append(cylinder(2.7, 0.82, x, y, body_height - 0.02))
        screw_holes.append(cylinder(0.7, 1.0, x, y, body_height + 0.17))
    body += Compound(bosses)
    body -= Compound(screw_holes)

    body += at(Sphere(2.45), 11.81, 44.86, body_height - 1.17)

    body -= Compound(
        [
            at(Box(4.0, 1.5, 5.0), 1.0, 6.7, 14.0),
            at(Box(4.0, 10.0, 3.8), 1.0, 10.0, 15.2),
            at(Box(4.0, 11.5, 4.8), 1.0, 21.5, 14.4),
        ]
    )
    body -= at(
        Box(12.0, 4.0, 3.4, align=(Align.MIN, Align.MIN, Align.MIN)),
        46.18,
        -1.0,
        9.5,
    )
    body -= cylinder(2.6, 4.0, 33.0, 2.0, 10.7, rotation=(90.0, 0.0, 0.0))

    side_button_profile = Plane.YZ * RectangleRounded(4.7, 7.8, 0.4)
    side_button_profile = at(side_button_profile, body_width - 0.05, 38.95, 11.55)
    body += extrude(side_button_profile, amount=1.35, dir=(1.0, 0.0, 0.0))
    body += cylinder(1.8, 1.7, 19.68, body_depth - 0.5, 14.0, rotation=(-90.0, 0.0, 0.0))
    return body
