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
def palm_pilot_battery_cover(overall_scale=1.0):
    """The observed battery cover as one connected removable part.

    overall_scale: scale the cover uniformly with the Pilot assembly.
    """
    shape=dict(_geometry.detailed_components())['Battery cover']
    if overall_scale!=1.0:
        shape=shape.scale(float(overall_scale),about=(0,0,0))
    if not shape.is_valid or len(shape.solids())!=1 or shape.volume<=0:
        raise ValueError('Battery cover must be one connected valid solid')
    return shape
