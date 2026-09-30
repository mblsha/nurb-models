"""Complete scanned Palm V exterior with smooth mirrored main forms and real controls."""
import json
from pathlib import Path
from nurb import *
from palm_complete_geometry import dock_components,power_control,contrast_control,dock_latch_tools,display_seat,complete_rocker_face,complete_rocker


@assembly
def palm_v_complete(front_sheet_mm=.65,rear_sheet_mm=.65,draft=False):
    pose=json.loads((Path(__file__).parents[1]/'references/palm-assembly-poses.json').read_text())['rear_cover']
    rear=use('palm_v_bottom_cover',sheet_thickness_mm=rear_sheet_mm)
    rear=rear.rotate(Axis.X,pose['rotation_x_degrees']).translate(tuple(pose['translation_mm']))
    front=use('palm_v_complete_front',sheet_thickness_mm=front_sheet_mm)
    frame=use('palm_v_complete_frame')
    for cutter in dock_latch_tools():frame=frame-cutter
    display=use('palm_v_display')
    rocker=use('palm_v_complete_scroll')
    rocker_backing=complete_rocker(.40,clearance=.16,vertical_offset=-.22)
    dock,contacts=dock_components()
    shapes=[(rear,'Rear aluminium shell',(.70,.71,.72)),(front,'Front aluminium shell',(.77,.78,.79)),(frame,'Smooth paired stylus channels',(.12,.13,.14)),(display,'Display and handwriting surface',(.37,.43,.33)),(display_seat(),'Display edge seat',(.10,.11,.12)),(rocker,'Scroll rocker',(.19,.20,.21)),(rocker_backing,'Scroll recess backing',(.10,.11,.12)),(dock,'Rear dock housing',(.11,.12,.13)),(power_control(),'Power button',(.17,.18,.19)),(contrast_control(),'Contrast button',(.22,.23,.24))]
    for x,y,z,name in [(-26.2,-42,3.8,'Left outer application key'),(-13,-44,4.2,'Left inner application key'),(13,-44,4.2,'Right inner application key'),(26.2,-42,3.8,'Right outer application key')]:
        shapes.append((use('palm_v_button').translate((x,y,z)),name,(.20,.21,.22)))
        seat=Cylinder(3.78,.55,align=(Align.CENTER,Align.CENTER,Align.MIN)).translate((x,y,z+.10))
        shapes.append((seat,name+' edge seat',(.10,.11,.12)))
    for i,contact in enumerate(contacts,1):
        shapes.append((contact,f'Recessed dock contact {i}',(.58,.49,.26)))
    for x in [-20.5,20.5]:
        shapes.append((Sphere(.82).translate((x,-47.3,-5.75)),f'Rear locating nub {"left" if x<0 else "right"}',(.70,.71,.72)))
    result=[]
    for shape,label,color in shapes:
        if not shape.is_valid or len(shape.solids())!=1:
            raise ValueError(f'{label} must be one valid exterior solid')
        shape.color=Color(*color)
        result.append(component(shape,label))
    return result
