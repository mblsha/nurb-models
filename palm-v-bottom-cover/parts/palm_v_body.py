"""Nominal symmetric intermediate Palm V chassis, from measured section profiles."""

import json
import math
from pathlib import Path

from nurb import *
from parts.palm_v_bottom_cover import exterior_surface, formed_blank
from palm_front_geometry import front_half
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.TopoDS import TopoDS
from OCP.BRepLib import BRepLib


def _profile_wire(axis, station, profile):
    points = [(station, a, b) if axis == 0 else (a, station, b) for a, b in profile]
    half = len(points) // 2
    return Wire(
        [
            Edge.make_spline(points[: half + 1]),
            Edge.make_spline(points[half:] + [points[0]]),
        ]
    )


def _loft(wires):
    builder = BRepOffsetAPI_ThruSections(True, False, 1e-6)
    builder.SetMaxDegree(3)
    builder.CheckCompatibility(False)
    for wire in wires:
        builder.AddWire(wire.wrapped)
    builder.Build()
    solid = TopoDS.Solid_s(builder.Shape())
    BRepLib.OrientClosedSolid_s(solid)
    return Solid(solid)


@part
def palm_v_body(rear_sheet_mm=0.65, front_sheet_mm=0.65, draft=False):
    """Smooth measured main frame; unresolved internal attachment details omitted."""
    data = json.loads(
        (
            Path(__file__).parents[1] / "references" / "palm-body-profile-fit.json"
        ).read_text()
    )
    rows = data["segments"]["right_rail"]["sections"]
    nominal = rows[-1]["profile"]
    profile = _profile_wire(1, -34, nominal)
    path = Wire(
        [
            Edge.make_line((36, -34, 0), (36, 50.7, 0)),
            Edge.make_three_point_arc(
                (36, 50.7, 0), (34.82842712, 53.52842712, 0), (32, 54.7, 0)
            ),
            Edge.make_line((32, 54.7, 0), (-32, 54.7, 0)),
            Edge.make_three_point_arc(
                (-32, 54.7, 0), (-34.82842712, 53.52842712, 0), (-36, 50.7, 0)
            ),
            Edge.make_line((-36, 50.7, 0), (-36, -34, 0)),
        ]
    )
    result = Solid.sweep(profile, path, is_frenet=False)
    low_rows = [r for r in rows if r["station"] < -33]
    # Ease the measured flare into the bent return to reduce the exterior tangent jump.
    low_rows.insert(1, {
        "station": -43.5,
        "profile": [
            (x0 + 0.2 * (x1 - x0), z0 + 0.2 * (z1 - z0))
            for (x0, z0), (x1, z1) in zip(rows[0]["profile"], rows[1]["profile"])
        ],
    })
    low_rows.append({"station": -33.5, "profile": nominal})
    lower = _loft([_profile_wire(1, r["station"], r["profile"]) for r in low_rows])
    result = result.fuse(lower).fuse(lower.mirror(Plane.YZ))
    ang = math.radians(-80)
    mid = math.radians(-40)
    bend_path = Edge.make_three_point_arc(
        (37.5, -45, 0),
        (34 + 3.5 * math.cos(mid), -45 + 3.5 * math.sin(mid), 0),
        (34 + 3.5 * math.cos(ang), -45 + 3.5 * math.sin(ang), 0),
    )
    bend = Solid.sweep(
        _profile_wire(1, -45, rows[0]["profile"]), bend_path, is_frenet=False
    )
    result = result.fuse(bend).fuse(bend.mirror(Plane.YZ))

    for name in ["bottom_bridge", "bottom_right_return"]:
        segment = data["segments"][name]
        piece = _loft(
            [
                _profile_wire(segment["axis"], r["station"], r["profile"])
                for r in segment["sections"]
            ]
        )
        result = result.fuse(piece)
        if name == "bottom_right_return":
            result = result.fuse(piece.mirror(Plane.YZ))
    bottom_points = [
        (float(x), -57.60 + 0.0053 * x * x, -12) for x in range(-44, 45, 4)
    ]
    outline = Wire(
        [
            Edge.make_spline(bottom_points),
            Edge.make_line(bottom_points[-1], (44, 65, -12)),
            Edge.make_line((44, 65, -12), (-44, 65, -12)),
            Edge.make_line((-44, 65, -12), bottom_points[0]),
        ]
    )
    clipped = result.intersect(extrude(Face(outline), amount=24))
    result = Compound(clipped) if isinstance(clipped, list) else clipped
    notch = Pos(0, 48.1, -6.35) * Box(12.2, 12.0, 7.3)
    result = result.cut(notch)
    # Measured deliberate internal features remain asymmetric.
    tabs = [
        (-32.5, 37.0, -1.1, 4.1, 17.0, 2.0),
        (32.0, 43.0, -1.1, 4.8, 10.0, 2.0),
        (29.5, -6.6, -2.8, 10.0, 2.5, 4.5),
        (32.0, -14.2, -3.0, 5.0, 3.6, 3.8),
        (-32.3, 19.0, -2.35, 5.0, 2.7, 5.0),
        (-31.5, -38.6, -2.95, 6.5, 1.7, 3.8),
    ]
    for x, y, z, w, h, depth in tabs:
        tab = Pos(x, y, z - depth / 2) * extrude(
            RectangleRounded(w, h, min(0.6, h / 3)), amount=depth
        )
        result = result.fuse(tab)
    for sign in [-1, 1]:
        stem = Pos(sign * 18.5, -47.1, -2.75) * Box(3.0, 11.0, 3.8)
        hook = Pos(sign * 15.7, -42.6, -2.75) * Box(7.9, 2.3, 3.8)
        result = result.fuse(stem).fuse(hook)
    rear_slot = Pos(-26.5, 50.5, -5.4) * extrude(
        RectangleRounded(7.6, 2.2, 0.55), amount=3.6
    )
    result = result.cut(rear_slot)
    # The denser paired master keeps the nominal metal seat numerically stable.
    half = Solid.thicken(exterior_surface(smooth_split_end=False), rear_sheet_mm, normal_override=(0, 0, 1))
    inner = max(
        (f for f in half.faces() if f.geom_type == GeomType.OFFSET),
        key=lambda f: f.area,
    )
    seat_clips = [
        Pos(35.9, 5, 0) * Box(4.6, 80, 20),
        # Reach the nominal far inner edge; the face intersection trims the clip.
        Pos(16, 53.1, 0) * Box(32, 4.2, 20),
        Pos(27, -54.5, 0) * Box(20, 4, 20),
    ]
    pose = json.loads(
        (Path(__file__).parents[1] / "references/palm-assembly-poses.json").read_text()
    )["rear_cover"]
    translation = list(pose["translation_mm"])
    translation[2] += 0.8
    placement = Pos(*translation) * Rot(X=pose["rotation_x_degrees"])
    corner_support_outline = Polygon(
        (31.3, 53.2), (35.4, 53.2), (35.4, 54.45),
        (34.8, 54.7), (34, 54.92), (33, 55.08),
        (31.3, 55.23), align=None,
    )
    corner_support = placement * (
        Pos(0, 0, 1.8) * extrude(corner_support_outline, amount=5.7)
    )
    result = result.fuse(corner_support).fuse(corner_support.mirror(Plane.YZ))
    for clip in seat_clips:
        patches = inner.intersect(clip)
        faces = (
            patches.faces()
            if hasattr(patches, "faces")
            else [f for item in patches for f in item.faces()]
        )
        for face in faces:
            # A clipped offset face can leave a zero-scale sliver at the far
            # corner; extruding it gives a negative-volume Boolean tool.
            if face.area < 1e-4:
                continue
            below = placement * Solid.extrude(face, (0, 0, -12))
            result = result.cut(below).cut(below.mirror(Plane.YZ))
            seat = placement * Solid.extrude(face, (0, 0, 2.6))
            result = result.fuse(seat).fuse(seat.mirror(Plane.YZ))
    master = placement * formed_blank(sheet_thickness_mm=rear_sheet_mm, smooth_split_end=False)
    result = result.cut(master)
    # The master cut can detach small pieces of the observed rear ledge below
    # the nominal contact surface. Those are removed as a design correction.
    solids = sorted(result.solids(), key=lambda solid: solid.volume, reverse=True)
    discarded = [solid.volume for solid in solids[1:]]
    if sum(discarded) > 8 or any(volume > 3 for volume in discarded):
        raise ValueError(
            "Rear interface separated substantial body material; inspect the chosen gauge"
        )
    result = solids[0]
    front = Solid.thicken(front_half(), front_sheet_mm, normal_override=(0, 0, -1))
    front = front.fuse(front.mirror(Plane.YZ)).translate((0, 0, 0.8))
    result = result.cut(front)
    solids = sorted(result.solids(), key=lambda solid: solid.volume, reverse=True)
    if sum(solid.volume for solid in solids[1:]) > 3:
        raise ValueError(
            "Front interface separated substantial body material; inspect its gauge"
        )
    result = solids[0]
    # The inward top rear ledge is a measured molded feature, wider than the C rail.
    ledge = Pos(0, 51, -3.6) * Box(66, 4.5, 2.7)
    patch = inner.intersect(Pos(17, 50, 0) * Box(34, 8, 20))
    for face in patch.faces():
        below = placement * Solid.extrude(face, (0, 0, -12))
        ledge = ledge.cut(below).cut(below.mirror(Plane.YZ))
    ledge = ledge.cut(notch).cut(rear_slot).cut(master)
    result = result.fuse(ledge)
    lower_corner_outline = Polygon(
        (33.8, 54.2), (35.2, 54.2), (35.2, 54.55),
        (35, 54.52), (34.5, 54.65), (33.8, 54.82), align=None,
    )
    lower_corner_support = placement * (
        Pos(0, 0, 0.4) * extrude(lower_corner_outline, amount=3.0)
    )
    result = result.fuse(lower_corner_support).fuse(lower_corner_support.mirror(Plane.YZ))
    result = result.cut(master)
    # The formed sheet falls just below the molded support at the shoulder.
    # Grow a narrow seat from its exact inner offset face to close that gap.
    shoulder_clip = Pos(33.35, 54.55, 0) * Box(1.9, 0.6, 20)
    for face in inner.intersect(shoulder_clip).faces():
        if face.area < 1e-4:
            continue
        shoulder_seat = placement * Solid.extrude(face, (0, 0, 0.45))
        result = result.fuse(shoulder_seat).fuse(shoulder_seat.mirror(Plane.YZ))
    if not result.is_valid or len(result.solids()) != 1:
        raise ValueError("The nominal body must be one valid connected solid")
    return result
