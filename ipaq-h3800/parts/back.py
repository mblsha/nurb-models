"""Rear cover reconstructed as a skin, formed channels and stepped fastener seats."""
from nurb import *
from case_profiles import back_height, rear_outline, REAR_HOLES, rear_catches, back_section_point, rear_outer_face


def _skin(length,width,gauge,seam):
    """Thicken the measured parametric surface along its true normals."""
    face=rear_outer_face(length,width,seam)
    sheet=Solid.thicken(face,gauge,normal_override=(0,0,1))
    return sheet


def _above_skin(length,width,seam,inset=.18):
    """Keep every interior addition above the same smooth exterior surface."""
    face=Pos(0,0,inset)*rear_outer_face(length,width,seam)
    above=Solid.extrude(face,(0,0,35))
    return above


def _shoulder_return(length,width,seam):
    """The curled lip observed inside the front's asymmetric side bulge."""
    sections=[]
    for x,root in [(32,38.8),(35,38.5),(38,38.0),(40,38.1),(43,38.4),(46,38.4),(48,38.4),(51,38.5),(53,38.4),(54,38.3),(55,38.3)]:
        xx=x*length/116.7;root*=width/79.2
        edge,edge_z=back_section_point(xx,39.6,length,width,seam)
        span=edge-root;base=back_height(xx,root,length,width,seam)
        upper=[(root,base+.22),(root+.035*span,(base+edge_z-.8)/2),(root+.16*span,edge_z-.8),(root+.4*span,edge_z-.65),(root+.7*span,edge_z-.35),(edge,edge_z+.25)]
        lower=[(root+span*t,back_height(xx,root+span*t,length,width,seam)-.05) for t in [0,.15,.35,.6,.8,1]]
        wire=Wire([Spline(*upper).edge(),Line(upper[-1],lower[-1]).edge(),Spline(*reversed(lower)).edge(),Line(lower[0],upper[0]).edge()])
        sections.append(Plane(origin=(xx,0,0),x_dir=(0,1,0),z_dir=(1,0,0))*make_face(wire))
    return loft(sections)


@part
def back(length=116.7, width=79.2, gauge=0.4, mating_z=-4.3, screw_hole=2.4, screw_seat=4.0, offset_x=4.10, offset_y=0.45, yaw=-0.308, draft=False):
    """Thin curved cover with the scan's asymmetric inner rail and mounting seats.

    length: Length of the rear cover before the small end tabs.
    width: Basic width before the one-sided flared shoulder.
    gauge: Thickness of the broad shell skin.
    mating_z: Elevation of the long rim where the front and back meet.
    screw_hole: Through clearance in the four stepped screw seats.
    screw_seat: Diameter of each exterior screw recess.
    offset_x: Fixed scan registration along the device.
    offset_y: Fixed scan registration across the device.
    yaw: Fixed angular registration to the front mounting pattern.
    """
    if not .2<=gauge<=1.2:reject('Use a skin gauge from 0.2 to 1.2 mm',param='gauge')
    if not 1.5<=screw_hole<screw_seat-1:reject('The screw recess must be at least 1 mm wider than its through hole',param='screw_hole')
    sx,sy=length/116.7,width/79.2;dz=mating_z+4.3
    skin=_skin(length,width,gauge,mating_z)
    inside=_above_skin(length,width,mating_z,min(gauge*.4,.18))
    details=[]
    def prism(x,y,l,w,top,r=.5,bottom=-18):
        return Pos(x*sx,y*sy,bottom+dz)*extrude(RectangleRounded(l*sx,w*sy,min(r*sx,r*sy)),amount=top-bottom)
    # The scan has three raised inner rails separated by two deliberate low gaps.
    for a,b in [(-41,-26),(-17,-3),(5,33)]:
        rail=prism((a+b)/2,-29.55,b-a,.85,-6.9,.35)
        top_edges=[e for e in rail.edges() if abs(e.center().Z-(-6.9+dz))<1e-5]
        details.append(fillet(top_edges,.2))
    # Smooth transverse braces replace the lumpy scanned reinforcement between rail and rim.
    for x in [-35.8,-12.7,16.0]:
        yz=[(-38.6,-4.8),(-37.2,-6.1),(-35.5,-9.25),(-34.0,-9.8),(-32.5,-8.6),(-31.0,-8.1),(-29.1,-6.9)]
        pts=[(y*sy,z+dz) for y,z in yz]
        wire=Wire([Spline(*pts).edge(),Line(pts[-1],(pts[-1][0],-18+dz)).edge(),Line((pts[-1][0],-18+dz),(pts[0][0],-18+dz)).edge(),Line((pts[0][0],-18+dz),pts[0]).edge()])
        brace=extrude(Plane(origin=(x*sx-.6,0,0),x_dir=(0,1,0),z_dir=(1,0,0))*make_face(wire),amount=1.2,dir=(1,0,0))
        details.append(brace)
    # Broader end bridges and their open undersides, observed at both ends of this rail.
    for x,l,top in [(-50,13.5,-5.0),(51.0,9.0,-5.3)]:
        bridge=prism(x,-33.35,l,8.6,top,1.1)
        underside=prism(x,-33.25,l-1.8,6.6,top-.7,.7,-18)
        details.append(bridge-underside)
    # Long rims have a returned locating lip, with discrete raised catches.
    details.append(prism(1,-38.65,101,1.45,-4.25,.35,-7.4))
    details.append(prism(-9,38.65,81,1.45,-4.25,.35,-7.4))
    details.extend(rear_catches(length,width,mating_z))
    details.append(_shoulder_return(length,width,mating_z))
    # Measured mounting webs at the two ends connect the seats to the side structures.
    details.append(prism(-47,30.5,10.5,1.2,-10.8,.4))
    details.append(prism(-49.8,27.9,1.2,6.5,-10.8,.4))
    details.append(prism(-53.3,25.2,7.7,1.2,-11.0,.4))
    ramp=Pos(40*sx,-27.4*sy,-18+dz)*Rot(0,0,23)*extrude(RectangleRounded(11*sx,3.1*sy,.8),amount=7.6)
    details.append(ramp)
    # Small pads are present in the scan on the plain half of the inner skin.
    details.append(prism(1,32.8,10.5,4.8,-10.45,.8))
    details.append(prism(-44,0,3.5,16.5,-13.2,.8))
    # Four tapered seats blend into the shell; their recess is cut from the exterior below.
    for x,y in REAR_HOLES:
        z=back_height(x*sx,y*sy,length,width,mating_z)
        seat=loft([Pos(x*sx,y*sy,z-.1)*Circle(3.3),Pos(x*sx,y*sy,z+.85)*Circle(2.8),Pos(x*sx,y*sy,-10.1+dz)*Circle(2.45),Pos(x*sx,y*sy,-8.6+dz)*Circle(2.35)])
        details.append(seat)
        # Short webs tie the mounting seats to the adjacent rail instead of isolated tubes.
        side=1 if y>0 else -1
        details.append(prism(x, y+side*3.1,1.1,5.4,-10.6,.35))
    # Fuse after clipping to the inside surface: the outer skin remains continuous.
    for addition in details:
        clipped=addition&inside
        if clipped:skin+=clipped
    skin &= Pos(0,0,-25)*extrude(rear_outline(length,width),amount=35)
    for x,y in REAR_HOLES:
        skin-=Pos(x*sx,y*sy,-20)*Cylinder(screw_hole/2,20,align=(Align.CENTER,Align.CENTER,Align.MIN))
        outer_z=back_height(x*sx,y*sy,length,width,mating_z)
        recess=Pos(x*sx,y*sy,-20)*Cylinder(screw_seat/2,outer_z+20+1.1,align=(Align.CENTER,Align.CENTER,Align.MIN))
        recess+=Pos(x*sx,y*sy,outer_z+.85)*Cone(screw_seat/2,screw_hole/2,.8,align=(Align.CENTER,Align.CENTER,Align.MIN))
        skin-=recess
        # The taller bridge follows the outside of the front screw post with 0.25 mm relief.
        skin-=Pos(x*sx,y*sy,-8.35+dz)*Cylinder(2.95,12,align=(Align.CENTER,Align.CENTER,Align.MIN))
    # Rounded bent tabs continue the two navigation mounting lands past the repaired flat end.
    for x,y in REAR_HOLES[2:]:
        stem=prism(-56.8,y,1.0,5.2,-8.25,.35)
        skin+=stem&inside
        skin+=prism(-59.3,y,5.9,5.2,-8.25,.75,-8.85)
    return Pos(offset_x,offset_y,0)*Rot(0,0,yaw)*skin.fix()
