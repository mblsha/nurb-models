"""Smooth whole-device side channels; hidden frame internals are not reconstructed."""
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import make_interp_spline
from nurb import *
from OCP.Geom import Geom_BSplineCurve
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array1OfPnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from palm_front_geometry import arrays


def smooth_edge(points,t,start,end):
    fit=make_interp_spline(t,points,k=3,bc_type=([(1,start)],[(1,end)]))
    poles=TColgp_Array1OfPnt(1,len(fit.c))
    for i,p in enumerate(fit.c,1):poles.SetValue(i,gp_Pnt(*p))
    knots,mults=arrays(fit.t)
    return Edge(BRepBuilderAPI_MakeEdge(Geom_BSplineCurve(poles,knots,mults,3)).Edge())


def outline(row,upper_t,lower_t):
    points=np.array([[x,y,row['z_mm']] for x,y in row['half_outline_xy_mm']])
    # Separate straight rail from its end blends: a global interpolant bows even
    # between identical width landmarks, importing a ripple into nominal tooling.
    right=[smooth_edge(points[:9],upper_t,[1.,0.,0.],[0.,-1.,0.]),Edge.make_line(points[8],points[12]),smooth_edge(points[12:],lower_t,[0.,-1.,0.],[-1.,0.,0.])]
    return Wire([*right,*[edge.mirror(Plane.YZ) for edge in right]])


@part
def palm_v_complete_frame(draft=False):
    rows=json.loads((Path(__file__).parents[1]/'references/complete-frame-fit.json').read_text())['levels']
    mean=np.mean([row['half_outline_xy_mm'] for row in rows],axis=0)
    upper_t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(mean[:9],axis=0),axis=1))]
    lower_t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(mean[12:],axis=0),axis=1))]
    body=Solid.make_loft([outline(row,upper_t,lower_t) for row in rows],ruled=False)
    # A simple unseen hollow keeps this an exterior surrogate, not invented electronics.
    body=body-Box(64,94,20).translate((0,2,0))
    if not body.is_valid or len(body.solids())!=1:
        raise ValueError('Whole-device side-channel frame must be one valid solid')
    return body
