from pathlib import Path

from nurb import *


REFERENCE = Path(__file__).resolve().parents[1] / "references" / "neewer-outer-focus-sleeve.step"


@part
def neewer_outer_focus_sleeve(draft=False):
    """Exact supplied sleeve that tightly fits the GM-MP2 large focus knob."""
    sleeve = import_step(REFERENCE)
    # The source STEP's axis is X and its origin belongs to the scanned assembly.
    # Stand the same untouched B-rep on its circular end for direct printing.
    return Pos(17.2, 0.0, 17.0) * Rot(0.0, -90.0, 0.0) * sleeve
