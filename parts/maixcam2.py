from nurb import *


@assembly
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
    draft=False,
):
    """The complete MaixCAM2 reconstruction assembled from printable sibling parts."""
    body_width = float(body_width)
    body_depth = float(body_depth)
    body_height = float(body_height)
    corner_radius = float(corner_radius)
    grille_rib_height = float(grille_rib_height)
    camera_center_x = float(camera_center_x)
    camera_center_y = float(camera_center_y)
    camera_neck_radius = float(camera_neck_radius)
    camera_cap_radius = float(camera_cap_radius)
    body = use(
        "maixcam2_body",
        body_width=body_width,
        body_depth=body_depth,
        body_height=body_height,
        corner_radius=corner_radius,
        grille_rib_height=grille_rib_height,
        camera_center_x=camera_center_x,
        camera_center_y=camera_center_y,
    )
    socket_z = body_height + 0.05 - 2.4
    left_pmod = Pos(11.35, 38.65, socket_z) * use("pmod_socket")
    right_pmod = Pos(55.26, 38.68, socket_z) * use("pmod_socket")
    camera_base = Pos(camera_center_x, camera_center_y, body_height) * use("maixcam2_camera_base")
    camera_mount = Pos(camera_center_x, camera_center_y, body_height) * use("maixcam2_camera_mount")
    lens = Pos(camera_center_x, camera_center_y, body_height + 1.0) * use(
        "maixcam2_lens",
        neck_radius=camera_neck_radius,
        cap_radius=camera_cap_radius,
    )
    return body, left_pmod, right_pmod, camera_base, camera_mount, lens
