from nurb import *
from build123d import SkipClean
from case_profiles import front_height, portable_solid, mounted_holes, rear_floor_volume, rear_cover_pocket, front_envelope, board_outline, REAR_X, REAR_Y, REAR_YAW, REAR_HOLES, rear_catches, front_shoulder_return


@part
def front(length=134.0, width=80.2, mate_z=-4.3, wall=1.0, window_length=78.5, window_width=59.1, window_x=4.25, window_y=1.75, nav_length=13.5, nav_width=30.0, nav_x=-52.0, boss_diameter=5.4, screw_diameter=2.4, pcb_top_z=-7.5, draft=False):
    """Measured rounded bezel, end caps and mounting posts.

    mate_z: Exposed outer case seam, independent of the PCB plane.
    wall: Nominal plastic thickness; hidden interior is reconstructed.
    """
    if wall <= 0 or wall > 2.5:
        reject("Use a shell wall between zero and 2.5 mm", param="wall")
    # Unite the sketch before offsetting it; the seat must be one cutter.
    pocket=rear_cover_pocket(float(mate_z))
    with SkipClean():
        # The bounded spline panels keep the returning end faces stable.
        mass=front_envelope(length,width).fix()
        cavity=front_envelope(length,width,wall).fix()
        # The front follows the shared cover section under both ends and around the flared shoulder.
        # Its back opening is cut from the same perimeter that defines the cover.
        floor=rear_floor_volume(float(mate_z))
        # Keep the surface panels separate so OCCT trims both sides of a return.
        apron=((mass & floor)-(Pos(0,0,wall)*floor)).fix()
        shell=(((mass-cavity).fix()&floor).fix()+apron).fix()
        shell=(shell-pocket).fix()
        shell-=Pos(window_x,window_y,-20)*extrude(RectangleRounded(window_length,window_width,.5),amount=40)
        shell-=Pos(nav_x,1.5,-3)*extrude(Ellipse(nav_length/2,nav_width/2),amount=20)
        for x,y in [(-50,27),(-45,20),(-50,-23),(-45,-17),(57,-16)]:
            shell-=Pos(x,y,-3)*Cylinder(3,20,align=(Align.CENTER,Align.CENTER,Align.MIN))
        # Preserve the measured five-slot grille in the front shell.
        for x in [53.8,55.6,57.4,59.2,61.0]:
            shell-=Pos(x,2,-3)*extrude(RectangleRounded(.85,18,.4),amount=20)
        # Main connector openings visible in the two end-on scan views.
        shell-=Pos(65,2,-9.1)*Box(20,24,3.4)
        shell-=Pos(65,-32.5,-8.5)*Rot(0,90,0)*Cylinder(3,20)
        shell-=Pos(65,33.5,-4.8)*Rot(0,90,0)*Cylinder(1.5,20)
        shell-=Pos(-69,0,-10.6)*Box(17,49,5.8)
        shell-=Pos(-64,1,-3)*Box(20,14,1.8)
        shell-=Pos(-64,-23,-3.4)*Rot(0,90,0)*Cylinder(.9,20)
        # Relief around the rear collars and the two end tabs beneath the board.
        for x,y in mounted_holes():
            shell-=Pos(x,y,-8.35)*Cylinder(3.25,12,align=(Align.CENTER,Align.CENTER,Align.MAX))
        rear_pose=Pos(REAR_X,REAR_Y,0)*Rot(0,0,REAR_YAW)
        for _,y in REAR_HOLES[2:]:
            shell-=rear_pose*Pos(-60.05,y,-8.5)*Box(5.8,5.4,1.1)
        # Internal receivers clear the returned rim catches without opening the exterior.
        for receiver in rear_catches(seam_z=float(mate_z),clearance=.2):
            shell-=rear_pose*receiver
        # Keep the nominal board clear without changing the exposed shell.
        shell-=Pos(0,0,pcb_top_z-1.2)*extrude(board_outline(clearance=.2),amount=1.4)
        for x,y in mounted_holes():
            ceiling=front_height(x,y,length,width)-wall+.25
            post=Pos(x,y,pcb_top_z)*Cylinder(boss_diameter/2,ceiling-pcb_top_z,align=(Align.CENTER,Align.CENTER,Align.MIN))
            bore=Pos(x,y,pcb_top_z-.1)*Cylinder(screw_diameter/2,ceiling-pcb_top_z-.35,align=(Align.CENTER,Align.CENTER,Align.MIN))
            shell=shell+post-bore
        # The returned shoulder is a local wrap with a shared three-dimensional back relief.
        shell=portable_solid(shell.fix())
        shell=(shell+front_shoulder_return(length,width,float(mate_z))).fix()
        return portable_solid(shell.fix())
