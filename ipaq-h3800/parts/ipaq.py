from nurb import *
from build123d import SkipClean
from case_profiles import front_height, speaker_region, portable_solid


@assembly
def ipaq(length=134.0, width=80.2, mating_z=-4.3, pcb_top_z=-7.5, exploded=0.0):
    """Measured exterior profiles with a simplified populated board.

    exploded: Spread the shells and display to inspect the interior.
    mating_z: Outer case seam, independent of the PCB elevation.
    """
    front_shift,back_shift=float(exploded)/2,-float(exploded)/2
    front=Pos(0,0,front_shift)*use('front',length=float(length),width=float(width),mate_z=float(mating_z),pcb_top_z=float(pcb_top_z))
    back=Pos(0,0,back_shift)*use('back',mating_z=float(mating_z))
    board=use('pcb',top_z=float(pcb_top_z))
    display=Pos(4.25,1.75,float(exploded)/3)*Box(78,58.6,2,align=(Align.CENTER,Align.CENTER,Align.MAX))
    # Both visible regions include the unified perimeter seat and matched curved returns.
    cap_region=Pos(0,0,front_shift)*speaker_region(float(length),float(width))
    with SkipClean():
        cap=portable_solid((front&cap_region).fix())
        front_body=portable_solid((front-cap_region).fix())
    solids=[component(front_body,'Front'),component(cap,'Speaker cap'),component(back,'Back'),component(board,'PCB'),component(display,'Display')]
    for name,x,y,sx,sy,height in [
        ('Processor',13,13.5,16,15,1.35),
        ('Memory A',-5,14,10,14,.8),
        ('Memory B',-5,-3.5,10,15,.65),
        ('Auxiliary IC',45,-23,9,9,1.0),
        ('Card socket',43.5,2,29,30,1.1),
        ('Navigation shield',-48,0,9,40,4.2),
        ('Lower connector',-7,-19,30,6,2.0),
        ('Upper connector',7.5,32,12,4,1.8),
    ]:
        block=Pos(x,y,float(pcb_top_z)-1)*Box(sx,sy,height,align=(Align.CENTER,Align.CENTER,Align.MAX))
        solids.append(component(block,name))
    nav=loft([Pos(-52,1.5,z+front_shift)*Ellipse(rx,ry) for z,rx,ry in [(2.65,6.3,14.6),(3.1,6.35,14.65),(3.55,5.95,14.1),(3.7,5.45,13.5)]])
    # Shallow thumb dish inside the raised oval perimeter.
    nav-=Pos(-52,1.5,43.4+front_shift)*Sphere(40.0)
    solids.append(component(nav,'Navigation'))
    for name,x,y in [('Button A',-50,27),('Button B',-45,20),('Button C',-50,-23),('Button D',-45,-17),('Power button',57,-16)]:
        z=front_height(x,y,float(length),float(width))
        dome=Pos(x,y,z-3.15+front_shift)*Sphere(4.1)
        limit=Pos(x,y,z-.35+front_shift)*Cylinder(2.72,1.6,align=(Align.CENTER,Align.CENTER,Align.MIN))
        button=dome&limit
        solids.append(component(button,name))
    return tuple(solids)
