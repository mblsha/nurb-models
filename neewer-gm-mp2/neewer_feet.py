"""Scan-envelope feet, with an explicitly provisional deployment mechanism."""
from nurb import *


def foot_profile():
    # The x=20 mm section has a nearly flat underside and 4.4 mm lower-side
    # rounds, from (y,z)=(5.0,4.42) through (7.1,0.5) to (9.4,0.02).
    # A 0.15 mm inset at each side keeps the provisional swing clear of the
    # independently measured Arca contact-flank endpoints.
    outline = Wire([
        Edge.make_line((0, 5.15, 4.42), (0, 39.05, 4.42)),
        Edge.make_three_point_arc((0, 39.05, 4.42), (0, 37.761, 1.309), (0, 34.65, .02)),
        Edge.make_line((0, 34.65, .02), (0, 9.55, .02)),
        Edge.make_three_point_arc((0, 9.55, .02), (0, 6.439, 1.309), (0, 5.15, 4.42)),
    ])
    return Pos(10.1, 0, 0) * Face(outline)


def folded_foot():
    return extrude(foot_profile(), 21.4, dir=(1, 0, 0))


def foot_at_angle(shape, angle):
    # Bay limits and the visible outer seam locate this provisional hinge.
    # The fused scan does not independently expose the hidden pivot cylinder.
    return Pos(10.1, 22.1, 4.42) * Rot(0, angle, 0) * Pos(-10.1, -22.1, -4.42) * shape


def opposite_foot(shape):
    return Pos(103.5, 22.1, 0) * Rot(0, 0, 180) * Pos(-103.5, -22.1, 0) * shape


def folding_feet(deployed=False, wrap=component):
    foot = foot_at_angle(folded_foot(), 65.0 if deployed else 0.0)
    return (
        wrap(foot, "left folding foot"),
        wrap(opposite_foot(foot), "right folding foot"),
    )


def foot_swing_clearance():
    # Only the hidden accommodation is inferred. Sweeping all boundary faces
    # gives the complete continuous occupied volume, so the fixed frame does
    # not depend on the displayed state or on sampled deployment angles.
    foot = folded_foot()
    sweeps = [revolve(face, axis=Axis((10.1, 0, 4.42), (0, 1, 0)), revolution_arc=65)
              for face in foot.faces()]
    envelope = foot.fuse(*sweeps)
    return envelope + opposite_foot(envelope)
