"""Scan-based exterior details for the complete Palm V, with no switch internals."""
import numpy as np
from scipy.interpolate import CubicSpline
from nurb import *
from palm_front_geometry import window_face

DOCK_Y=np.array([-56.3,-56.,-55.,-54.,-53.,-52.,-51.,-50.,-49.,-48.,-44.5])
DOCK_Z=np.array([-2.48,-2.64,-4.43,-5.33,-5.55,-5.70,-5.85,-5.92,-5.99,-6.07,-6.16])
DOCK_CURVE=CubicSpline(DOCK_Y,DOCK_Z,bc_type='natural')


def dock_strip(x0,x1,y0=-56.2,y1=-45.1,offset=0.0,thickness=1.5):
    ys=np.linspace(y0,y1,25)
    outer=[(0,float(y),float(DOCK_CURVE(y)+offset)) for y in ys]
    inner=[(x,y,z+thickness) for x,y,z in outer]
    face=Face(Wire([Edge.make_spline(outer),Edge.make_line(outer[-1],inner[-1]),Edge.make_spline(inner[::-1]),Edge.make_line(inner[0],outer[0])]))
    return extrude(face,amount=x1-x0,dir=(1,0,0)).translate((x0,0,0))


def dock_outline():
    right=[Edge.make_bezier((0,-45.2,0),(6,-45.3,0),(12,-46.5,0),(15.9,-48.1,0)),Edge.make_line((15.9,-48.1,0),(15.9,-55.1,0)),Edge.make_bezier((15.9,-55.1,0),(10,-55.9,0),(5,-56.4,0),(0,-56.45,0))]
    return Face(Wire([*right,*[e.mirror(Plane.YZ) for e in right]]))


def dock_components():
    body=dock_strip(-15.9,15.9)
    trim=extrude(dock_outline(),amount=20,dir=(0,0,1)).translate((0,0,-10))
    body=body & trim
    for x in range(-9,10,2):
        body=body-dock_strip(x-.57,x+.57,-54.1,-48.05,offset=-1,thickness=1.62)
    # The paired latch recesses are deep, unlike the ten shallow contact lanes.
    for cutter in dock_latch_tools():
        body=body-cutter
    contacts=[dock_strip(x-.40,x+.40,-53.85,-48.25,offset=.56,thickness=.08) for x in range(-9,10,2)]
    return body,contacts


def power_control(clearance=0):
    return extrude(Ellipse(4.0+clearance,1.6+clearance),amount=1.2).translate((24.2,55.9,3.86))


def contrast_control(clearance=0):
    return extrude(RectangleRounded(7.3+2*clearance,2.55+2*clearance,.4+clearance),amount=.65).translate((-24.0,50.8,4.55))


def dock_latch_tools():
    return [extrude(RectangleRounded(2.8,6.0,.65),amount=5.4).translate((x,-52,-8)) for x in [-12.0,12.0]]


def display_seat():
    # Only the opaque seat behind the measured glass edge is established here;
    # its unseen thickness is a nominal closure rather than an electronics model.
    body=extrude(window_face(.6),amount=1.75,dir=(0,0,1)).translate((0,0,2.5))
    clear=extrude(window_face(-.15),amount=10,dir=(0,0,1)).translate((0,0,2.8))
    return body-clear


def complete_rocker_face(clearance=0.0):
    w=3.7+clearance
    waist=2.6+clearance
    runs=[[(0,7.3+clearance),(2.4,7.3+clearance),(w,6.7),(w,4.7)],[(w,4.7),(w,3.3),(waist,2),(waist,0)],[(waist,0),(waist,-2),(w,-3.3),(w,-4.7)],[(w,-4.7),(w,-6.7),(2.4,-7.3-clearance),(0,-7.3-clearance)]]
    right=[Edge.make_bezier(*[(x,-45.65+y*(15.1/14.6),0) for x,y in run]) for run in runs]
    return Face(Wire([*right,*[edge.mirror(Plane.YZ) for edge in right]]))


def complete_rocker(thickness=1.4,clearance=-.10,vertical_offset=0.0):
    stations=[(-54,2.61),(-52.6,4.0),(-51,4.50),(-49,5.13),(-47,5.83),(-45,6.18),(-43,6.29),(-41,6.24),(-39,6.50),(-38.3,6.02),(-37.5,5.19)]
    sections=[]
    for y,h in stations:
        h+=vertical_offset
        top=Edge.make_bezier((-4,y,h-.3),(-2,y,h+.1),(2,y,h+.1),(4,y,h-.3))
        sections.append(Wire([top,Edge.make_line((4,y,h-.3),(4,y,h-thickness)),Edge.make_line((4,y,h-thickness),(-4,y,h-thickness)),Edge.make_line((-4,y,h-thickness),(-4,y,h-.3))]))
    body=Solid.make_loft(sections,ruled=False)
    mask=extrude(complete_rocker_face(clearance),amount=12,dir=(0,0,1)).translate((0,0,-2))
    return body & mask
