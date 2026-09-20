"""Shared construction helpers for sibling parts in this project."""

from nurb import Align, Circle, Cylinder, Location, RectangleRounded, extrude


def at(shape, x=0.0, y=0.0, z=0.0):
    return shape.moved(Location((x, y, z)))


def rounded_prism(width, depth, radius, height, x=0.0, y=0.0, z=0.0):
    profile = RectangleRounded(width, depth, radius, align=(Align.MIN, Align.MIN))
    return extrude(at(profile, x, y, z), amount=height)


def disk(radius, x=0.0, y=0.0, z=0.0):
    return at(Circle(radius), x, y, z)


def cylinder(radius, height, x=0.0, y=0.0, z=0.0, rotation=(0.0, 0.0, 0.0)):
    shape = Cylinder(radius, height, rotation=rotation, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return at(shape, x, y, z)
