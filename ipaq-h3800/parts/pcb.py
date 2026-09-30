from nurb import *
from case_profiles import mounted_holes, board_outline, REAR_X, REAR_Y, REAR_YAW


@part
def pcb(length=116.0, width=71.0, thickness=1.0, top_z=-7.5, corner_cut=6.0, hole_diameter=2.6, draft=False):
    """Simplified board envelope with the measured mounting layout."""
    if thickness <= 0 or 2*corner_cut >= min(length,width):
        reject("Use positive board thickness and smaller corner cuts",param="thickness")
    outline=board_outline(length,width,corner_cut)
    board=Pos(0,0,top_z-thickness)*extrude(outline,amount=thickness)
    # This is a generic board envelope; the scan's rail needs the lower side relieved.
    rail_side=Pos(REAR_X,REAR_Y,0)*Rot(0,0,REAR_YAW)*Pos(0,-28.85,-20)*Box(200,100,30,align=(Align.CENTER,Align.MAX,Align.MIN))
    board-=rail_side
    for xx,yy in mounted_holes():
        board-=Pos(xx,yy,top_z-thickness-.1)*Cylinder(hole_diameter/2,thickness+.2,align=(Align.CENTER,Align.CENTER,Align.MIN))
    return board
