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

@part
def palm_pilot_body(overall_scale=1.0, screen_width=59.623, screen_height=80.551, button_width=8.5, shaft_diameter=5.180704, bore_allowance=.2):
    """Exportable fixed Pilot exterior, with both sliding rear covers excluded.

    overall_scale: scale the complete Pilot while preserving the measured proportions.
    screen_width: width of the display opening below its rolled rim.
    screen_height: height of the display opening below its rolled rim.
    button_width: diameter of the four application button caps.
    shaft_diameter: diameter of the cylindrical stylus the passage accepts.
    bore_allowance: nominal extra diameter in the unseen stylus passage.
    """
    pieces = _geometry.detailed_components(float(screen_width), float(screen_height), float(button_width), float(shaft_diameter), float(bore_allowance))
    fixed=[piece for name,piece in pieces if name not in ('Memory cover','Battery cover')]
    shape = fixed[0].fuse(*fixed[1:])
    if overall_scale != 1.0:
        shape = shape.scale(float(overall_scale), about=(0, 0, 0))
    return shape
