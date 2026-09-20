from nurb import *


def _at(shape, x=0.0, y=0.0, z=0.0):
    return shape.moved(Location((x, y, z)))


def _rounded_prism(width, depth, radius, height, x=0.0, y=0.0, z=0.0):
    profile = RectangleRounded(width, depth, radius, align=(Align.MIN, Align.MIN))
    return extrude(_at(profile, x, y, z), amount=height)


def _disk(radius, x, y, z):
    return _at(Circle(radius), x, y, z)


def _cylinder(radius, height, x, y, z, rotation=(0.0, 0.0, 0.0)):
    return _at(
        Cylinder(radius, height, rotation=rotation, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        x,
        y,
        z,
    )


def _pmod_socket(center_x, center_y, top_z, blocked=()):
    pitch = 2.54
    columns = 6
    rows = 2
    housing_width = columns * pitch
    housing_depth = rows * pitch
    housing_height = 2.4
    housing = _rounded_prism(
        housing_width,
        housing_depth,
        0.25,
        housing_height,
        center_x - housing_width / 2.0,
        center_y - housing_depth / 2.0,
        top_z - housing_height,
    )
    entrances = []
    for column in range(columns):
        for row in range(rows):
            if (column, row) in blocked:
                continue
            x = center_x + (column - (columns - 1) / 2.0) * pitch
            y = center_y + (row - (rows - 1) / 2.0) * pitch
            entrance = RectangleRounded(1.05, 1.05, 0.12, align=(Align.CENTER, Align.CENTER))
            entrances.append(extrude(_at(entrance, x, y, top_z - 1.25), amount=1.35))
    return housing - Compound(entrances)


@part
def maixcam2(
    body_width=66.5,
    body_depth=50.2,
    body_height=20.46,
    corner_radius=6.0,
    grille_rib_height=0.9,
    camera_center_x=33.5,
    camera_center_y=40.0,
    camera_neck_radius=6.0,
    camera_cap_radius=8.0,
    show_mount=True,
    draft=False,
):
    """A printable MaixCAM2 enclosure reconstruction with measured top-side interfaces.

    show_mount: show the separate flat camera adapter for fit inspection
    """
    if corner_radius <= 0.0:
        reject("corner_radius must be greater than zero", param="corner_radius")
    if grille_rib_height <= 0.0:
        reject("grille_rib_height must be greater than zero", param="grille_rib_height")
    if camera_cap_radius <= camera_neck_radius:
        reject("camera_cap_radius must be larger than camera_neck_radius", param="camera_cap_radius")

    body = _rounded_prism(body_width, body_depth, corner_radius, body_height)
    ribs = []
    for row in range(7):
        center_y = 10.8 + 3.14 * row
        ribs.append(
            loft(
                [
                    _at(SlotOverall(59.8, 1.9), 33.48, center_y, body_height - 0.02),
                    _at(SlotOverall(59.8, 1.4), 33.48, center_y, body_height + 0.65 * grille_rib_height),
                    _at(SlotOverall(59.8, 0.5), 33.48, center_y, body_height + grille_rib_height),
                ],
                ruled=False,
            )
        )
    body += Compound(ribs)
    adapter_rib_clearance = _at(
        Box(28.1, 0.2, grille_rib_height + 0.1, align=(Align.MIN, Align.MIN, Align.MIN)),
        camera_center_x - 14.05,
        camera_center_y - 9.55,
        body_height - 0.01,
    )
    body -= adapter_rib_clearance

    pmod_centers = ((11.35, 38.65), (55.26, 38.68))
    pmod_pockets = Compound(
        [
            _rounded_prism(15.9, 5.8, 0.5, 2.7, x - 7.95, y - 2.9, body_height - 2.5)
            for x, y in pmod_centers
        ]
    )
    body -= pmod_pockets
    pmod_reliefs = []
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
        pmod_reliefs.append(extrude(_at(SlotOverall(1.8, 1.1), x, y, body_height - 0.5), amount=1.0))
    body -= Compound(pmod_reliefs)
    left_pmod = _pmod_socket(*pmod_centers[0], body_height + 0.05)
    right_pmod = _pmod_socket(*pmod_centers[1], body_height + 0.05)
    left_pmod.label = "left PMOD 2x6 female socket"
    right_pmod.label = "right PMOD 2x6 female socket"

    boss_centers = ((5.3, 5.1), (61.0, 5.0), (5.4, 45.4), (61.2, 45.25))
    bosses = []
    screw_holes = []
    for x, y in boss_centers:
        bosses.append(_cylinder(2.7, 0.82, x, y, body_height - 0.02))
        screw_holes.append(_cylinder(0.7, 1.0, x, y, body_height + 0.17))
    body += Compound(bosses)
    body -= Compound(screw_holes)

    camera_z = body_height
    camera_ears = SlotOverall(26.3, 6.32, align=(Align.CENTER, Align.CENTER))
    camera_base = extrude(_at(camera_ears, camera_center_x, camera_center_y, camera_z - 0.02), amount=1.02)
    camera_base += _cylinder(8.72, 1.02, camera_center_x, camera_center_y, camera_z - 0.02)
    camera_lens = _cylinder(camera_neck_radius, 5.32, camera_center_x, camera_center_y, camera_z + 1.0)
    camera_lens += _cylinder(7.1, 2.12, camera_center_x, camera_center_y, camera_z + 6.28)
    shoulder = loft(
        [
            _disk(7.1, camera_center_x, camera_center_y, camera_z + 8.38),
            _disk(camera_cap_radius, camera_center_x, camera_center_y, camera_z + 9.5),
        ],
        ruled=False,
    )
    camera_lens += shoulder
    camera_lens += _cylinder(camera_cap_radius, 5.32, camera_center_x, camera_center_y, camera_z + 9.5)
    lens_recess = _cylinder(min(6.05, camera_cap_radius - 1.0), 0.8, camera_center_x, camera_center_y, camera_z + 14.31)
    camera_screws = Compound(
        [
            loft(
                [
                    _disk(1.15, x, camera_center_y, camera_z + 0.22),
                    _disk(1.65, x, camera_center_y, camera_z + 1.08),
                ],
                ruled=False,
            )
            for x in (camera_center_x - 10.0, camera_center_x + 10.0)
        ]
    )
    body += camera_base
    body -= camera_screws
    camera_lens -= lens_recess
    flat_camera_mount = None
    if show_mount:
        flat_camera_mount = import_step("references/maixcam2-camera-mount.step")
        flat_camera_mount = _at(flat_camera_mount, camera_center_x, camera_center_y, camera_z)
        flat_camera_mount.label = "flat camera adapter"
    camera_lens.label = "camera lens"

    body += _at(Sphere(2.45), 11.81, 44.86, body_height - 1.17)

    right_openings = Compound(
        [
            _at(Box(4.0, 1.5, 5.0), 1.0, 6.7, 14.0),
            _at(Box(4.0, 10.0, 3.8), 1.0, 10.0, 15.2),
            _at(Box(4.0, 11.5, 4.8), 1.0, 21.5, 14.4),
        ]
    )
    front_slot = _at(
        Box(12.0, 4.0, 3.4, align=(Align.MIN, Align.MIN, Align.MIN)),
        46.18,
        -1.0,
        9.5,
    )
    front_round = _cylinder(2.6, 4.0, 33.0, 2.0, 10.7, rotation=(90.0, 0.0, 0.0))
    body -= right_openings
    body -= front_slot
    body -= front_round

    side_button_profile = Plane.YZ * RectangleRounded(4.7, 7.8, 0.4)
    side_button_profile = _at(side_button_profile, body_width - 0.05, 38.95, 11.55)
    left_button = extrude(side_button_profile, amount=1.35, dir=(1.0, 0.0, 0.0))
    rear_button = _cylinder(1.8, 1.7, 19.68, body_depth - 0.5, 14.0, rotation=(-90.0, 0.0, 0.0))
    body += left_button
    body += rear_button

    components = [body, left_pmod, right_pmod]
    if flat_camera_mount is not None:
        components.append(flat_camera_mount)
    components.append(camera_lens)
    return Compound(components)
