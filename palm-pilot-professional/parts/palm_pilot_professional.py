from nurb import *
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location
import sys

_geometry_path=Path(__file__).resolve().parents[1]/"palm_pilot_geometry.py"
_stamp=(str(_geometry_path),_geometry_path.stat().st_mtime_ns)
_geometry=sys.modules.get("_palm_pilot_geometry")
if _geometry is None or getattr(_geometry,"_source_stamp",None)!=_stamp:
    _spec=spec_from_file_location("_palm_pilot_geometry",_geometry_path)
    _geometry=module_from_spec(_spec)
    _spec.loader.exec_module(_geometry)
    _geometry._source_stamp=_stamp
    sys.modules["_palm_pilot_geometry"]=_geometry

@assembly
def palm_pilot_professional(overall_scale=1.0,screen_width=59.623,screen_height=80.551,button_width=8.5,shaft_diameter=5.180704,stylus_withdrawal=0.0,bore_allowance=.2,battery_slide=0.0,memory_slide=0.0):
    """Rebuilt Pilot with separately sliding battery and memory covers.

    overall_scale: scale the entire assembly while retaining its measured proportions.
    screen_width: width of the display opening below its rolled rim.
    screen_height: height of the display opening below its rolled rim.
    button_width: diameter of the four application button caps.
    shaft_diameter: diameter of the clean fitted cylindrical stylus shaft.
    stylus_withdrawal: distance to slide the stylus out of its cavity.
    bore_allowance: nominal extra diameter for the unseen stylus passage.
    battery_slide: outward travel of the battery cover toward the left case edge, 0 to 60 mm.
    memory_slide: outward travel of the memory cover toward the product top, 0 to 60 mm.
    """
    # Register the body for normal CLI and viewer downloads; return the named pieces below.
    use('palm_pilot_body', overall_scale=float(overall_scale), screen_width=float(screen_width), screen_height=float(screen_height), button_width=float(button_width), shaft_diameter=float(shaft_diameter), bore_allowance=float(bore_allowance))
    use('palm_pilot_battery_cover',overall_scale=float(overall_scale))
    use('palm_pilot_memory_cover',overall_scale=float(overall_scale))
    if not 0<=battery_slide<=60 or not 0<=memory_slide<=60:
        raise ValueError('Cover travel must be between 0 and 60 mm outward')
    pieces=_geometry.detailed_components(float(screen_width),float(screen_height),float(button_width),float(shaft_diameter),float(bore_allowance))
    stylus=use('palm_pilot_stylus',shaft_diameter=float(shaft_diameter))
    stylus=Pos(36.0517,59.315-107.368+float(stylus_withdrawal),6.8262)*Rot(-90,0,0)*stylus
    pieces.append(('Stylus',stylus))
    result=[]
    for label,shape in pieces:
        if label=='Battery cover':
            shape=Pos(-float(battery_slide),0,-.004146*float(battery_slide))*shape
        elif label=='Memory cover':
            shape=Pos(0,float(memory_slide),.0085*float(memory_slide))*shape
        if not shape.is_valid or len(shape.solids())!=1 or shape.volume<=0:
            raise ValueError(f'{label} must remain one valid positive solid')
        if overall_scale!=1.0:
            shape=shape.scale(float(overall_scale),about=(0,0,0))
        component(shape,label)
        result.append(shape)
    for label in ['Front casing','Rear casing','Memory cover','Battery cover']:
        clearance(label,'Stylus',minimum=0.0)
    clearance('Memory cover','Rear casing',minimum=0.0)
    clearance('Battery cover','Rear casing',minimum=0.0)
    clearance('Memory cover','Battery cover',minimum=0.0)
    return tuple(result)
