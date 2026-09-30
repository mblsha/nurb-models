"""Accurate front skin with the complete-scan scroll opening and upper controls."""
from nurb import *
from palm_front_geometry import front_half,window_face,BUTTON_CENTERS
from palm_complete_geometry import complete_rocker_face,power_control,contrast_control


@part
def palm_v_complete_front(sheet_thickness_mm=.65,draft=False):
    if not .35<=sheet_thickness_mm<=.9:
        reject('Use a provisional front sheet gauge between 0.35 and 0.9 mm.','sheet_thickness_mm')
    half=Solid.thicken(front_half(),sheet_thickness_mm,normal_override=(0,0,-1))
    for face in [window_face(),complete_rocker_face(.12)]:
        half=half-extrude(face,amount=20,dir=(0,0,1)).translate((0,0,-10))
    for x,y in BUTTON_CENTERS:
        half=half-Cylinder(3.70,20).translate((x,y,0))
    body=half.fuse(half.mirror(Plane.YZ))
    body=body-power_control(.1)-contrast_control(.1)
    if not body.is_valid or len(body.solids())!=1:
        raise ValueError('Complete front cover did not form one valid sheet')
    return body
