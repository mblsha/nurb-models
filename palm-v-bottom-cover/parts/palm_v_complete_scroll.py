"""Smooth symmetric scroll rocker crown measured from the complete scan."""
from nurb import *
from palm_complete_geometry import complete_rocker


@part
def palm_v_complete_scroll(hidden_thickness_mm=1.4,draft=False):
    return complete_rocker(hidden_thickness_mm)
