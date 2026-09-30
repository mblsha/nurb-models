"""Smooth section measurements and the shared fastener datum, in millimetres."""
from math import exp, sqrt, sin, cos, radians, asin, degrees
from scipy.interpolate import PchipInterpolator
from nurb import *

# Exposed scan skin, excluding buttons, display and support material.
_front_y = PchipInterpolator([0,28,31.5,34,36,37,38,39,39.6,40.1,43], [1.38,1.38,1.34,1.23,.96,.65,.19,-.81,-1.85,-4.35,-23])
_back_y = PchipInterpolator([0,10,20,25,30,32,34,35,36,37,38,39,39.6], [3.64,3.49,3.0,2.69,2.14,1.62,.64,-.04,-.99,-2.12,-3.64,-5.74,-7.3])

# Centres fitted to the rear circular bores before assembly placement.
REAR_HOLES = ((53.41,28.77),(53.55,-26.76),(-49.86,25.21),(-49.65,-26.59))
REAR_X, REAR_Y, REAR_YAW = 4.10, .45, -.308


def mounted_holes():
    from math import sin,cos,radians
    a=radians(REAR_YAW)
    return [(REAR_X+x*cos(a)-y*sin(a),REAR_Y+x*sin(a)+y*cos(a)) for x,y in REAR_HOLES]


def front_height(x,y,length=134.0,width=80.2):
    u,v=float(x)*134/float(length),float(y)*80.2/float(width)
    # The two control areas have different footprints and different curvature.
    base=float(_front_y(abs(v)))
    if u < -34:
        base-=.42*min(1,(-u-34)/10)*exp(-(abs(v)/35)**8)
    elif u > 38:
        base-=.30*min(1,(u-38)/10)*exp(-(abs(v)/35)**8)
    nav=2.12*exp(-((u+52.3)/10.6)**4-((v-1.5)/20.7)**2)
    speaker=1.88*exp(-((u-59)/10.8)**6-((v-1.5)/21.2)**4)
    # The face rolls into both curved end walls, including the corners.
    if abs(v)<40.15:
        nav_edge=-11.9-sqrt(max(.01,55**2-v*v))
        top_edge=-28+sqrt(max(.01,95**2-v*v))
        dn=u-nav_edge;dt=top_edge-u
        for d,weight in [(dn,1.55),(dt,1.55)]:
            base-=weight*exp(-(max(0,d)/1.65)**2)+max(0,-d)*1.8
    return base+nav+speaker


def _ear_x(x):
    return exp(-((x-52.5)/11.4)**6)


def speaker_region(length=134.0,width=80.2):
    # Curved lower edge and swept sides of the IR/speaker cap, visible in scan texture.
    points=[(75,-23),(64,-23),(55,-22),(49.8,-20.7),(48.2,-17),(48,0),(48.5,18),(50,23),(55,25.4),(65,27),(75,27)]
    points=[(x*length/134,y*width/80.2) for x,y in points]
    wire=Wire([Spline(*points).edge(),Line(points[-1],points[0]).edge()])
    return Pos(0,0,-22)*extrude(make_face(wire),amount=35)


# The positive-Y speaker shoulder is intentional. Both scans show its mating curl.
_shoulder_spread=PchipInterpolator([-90,28,30,35,40,45,48,51,53.6,60,90],[0,0,0,.15,1.0,2.2,3.4,3.8,3.8,3.8,3.8])
_shoulder_drop=PchipInterpolator([-90,28,30,35,40,45,48,51,53.6,60,90],[0,0,0,-1.0,-2.5,-2.0,-1.65,-1.8,-1.95,-1.95,-1.95])
REAR_STATIONS=(-58.35,-52.5,-41,-23,0,20,28,30,32,35,38,40,43,45,48,50,52,53,53.6,54.2,55,56.5,58.35)


def back_section_point(x,v,length=116.7,width=79.2,seam_z=-4.3):
    """Measured rear section with its one-sided flared shoulder, in local rear coordinates."""
    u=float(x)*116.7/float(length)
    t=max(0,min(1,(float(v)-31.5)/8.1))
    y=(float(v)+float(_shoulder_spread(u))*t*t)*width/79.2
    bow=.7*(u/58.35)**2*max(0,1-(abs(v)/39.6)**4)
    z=float(seam_z)-7.3-float(_back_y(abs(v)))+bow+float(_shoulder_drop(u))*t**6
    return y,z


def rear_outer_face(length=116.7,width=79.2,seam_z=-4.3):
    """A single parameterized surface preserves the flared shoulder through its return."""
    vs=sorted({sign*v for sign in [-1,1] for v in [0,8,16,22,26,29,31,32,33,34,35,36,37,38,38.5,39,39.3,39.6]})
    xs=[x*length/116.7 for x in REAR_STATIONS]
    points=[[(x,*back_section_point(x,v,length,width,seam_z)) for v in vs] for x in xs]
    return surface_from_grid(points,xs,vs)


def back_height(x,y,length=116.7,width=79.2,seam_z=-4.3):
    u=float(x)*116.7/float(length);yy=float(y)*79.2/float(width)
    spread=float(_shoulder_spread(u))
    if yy>31.5 and spread>1e-10:
        d=yy-31.5;k=spread/(8.1**2)
        v=31.5+2*d/(1+sqrt(1+4*k*d))
    else:v=yy
    v=max(-39.6,min(39.6,v))
    return back_section_point(x,v,length,width,seam_z)[1]


def back_slope(x,y,length=116.7,width=79.2):
    e=.002
    return (back_height(x,y+e,length,width)-back_height(x,y-e,length,width))/(2*e)


def rear_outline(length=116.7,width=79.2,clearance=0.0):
    """Shared asymmetric cover outline, retaining the planar repaired navigation end."""
    sx,sy=length/116.7,width/79.2;hx,hy=length/2,width/2;corner=12.0*sx
    # Use the established navigation-end arcs and the lower half of the opposite ellipse.
    points=[(x*sx,y*sy) for x,y in [(57.3710,22),(56.4,28),(55.0,34),(54.05,40),(53.75,42.75),(52.7,43.2),(49,43.05),(46,42.05),(42,41.2),(38,40.1),(34,39.6),(29,39.6)]]
    end_angle=degrees(asin(22/39.6))
    ellipse=Edge.make_ellipse(5.8*sx,hy,Plane(origin=(52.55*sx,0,0)),start_angle=-90,end_angle=end_angle)
    points[0]=(ellipse.position_at(1).X,ellipse.position_at(1).Y)
    curved=Spline(*points,tangents=[(-.12*sx,sy,0),(-sx,0,0)]).edge()
    a=(-58.35*sx,-27.6*sy);b=(-46.35*sx,-39.6*sy);c=(52.55*sx,-39.6*sy)
    d=(-46.35*sx,39.6*sy);e=(-58.35*sx,27.6*sy)
    wire=Wire([ThreePointArc(a,(-54.835281*sx,-36.085281*sy),b).edge(),Line(b,c).edge(),ellipse,curved,Line(points[-1],d).edge(),ThreePointArc(d,(-54.835281*sx,36.085281*sy),e).edge(),Line(e,a).edge()])
    outline=make_face(wire)
    return offset(outline,amount=clearance) if clearance else outline


def _base_back_height(x,y,length=116.7,width=79.2,seam_z=-4.3):
    u=float(x)*116.7/float(length);v=abs(float(y))*79.2/float(width)
    bow=.7*(u/58.35)**2*max(0,1-(v/39.6)**4)
    return float(seam_z)-7.3-float(_back_y(v))+bow


def rear_floor_volume(seam_z=-4.3):
    """Volume above the shared outer skin, extended into the front end returns."""
    ys=sorted({sign*y for sign in [-1,1] for y in [0,10,20,25,30,32,34,35,36,37,38,38.5,39,39.2,39.4,39.5,39.6,39.65,39.7,39.8,40.1,42,45,50]})
    sections=[]
    for x in [-85,-70,-58.35,-52.515,-40.845,-20.4225,0,20.4225,40.845,52.515,58.35,70,85]:
        points=[(y,_base_back_height(max(-58.35,min(58.35,x)),max(-39.6,min(39.6,y)),seam_z=seam_z)) for y in ys]
        # Dense rim stations retain the measured slope through the side-to-seat turn.
        wire=Wire([Spline(*points).edge(),Line(points[-1],(50,20)).edge(),Line((50,20),(-50,20)).edge(),Line((-50,20),points[0]).edge()])
        sections.append(Plane(origin=(x,0,0),x_dir=(0,1,0),z_dir=(1,0,0))*make_face(wire))
    return Pos(REAR_X,REAR_Y,0)*Rot(0,0,REAR_YAW)*loft(sections)


def rear_cover_pocket(seam_z=-4.3, clearance=.2):
    """A complementary perimeter seat, open from the back up to the seam."""
    pocket=Pos(0,0,-35)*extrude(rear_outline(clearance=clearance),amount=35+seam_z+clearance)
    return Pos(REAR_X,REAR_Y,0)*Rot(0,0,REAR_YAW)*pocket

def surface_from_grid(points, u, v):
    """Interpolate in measured station coordinates rather than automatic chord length."""
    import numpy as np
    from scipy.interpolate import RectBivariateSpline
    from OCP.Geom import Geom_BSplineSurface
    from OCP.TColgp import TColgp_Array2OfPnt
    from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
    from OCP.gp import gp_Pnt
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    data=np.asarray(points)
    fits=[RectBivariateSpline(u,v,data[:,:,i],kx=3,ky=3,s=0) for i in range(3)]
    tx,ty=fits[0].get_knots();nx,ny=len(tx)-4,len(ty)-4
    cs=[f.get_coeffs().reshape(nx,ny) for f in fits]
    poles=TColgp_Array2OfPnt(1,nx,1,ny)
    for i in range(nx):
        for j in range(ny):poles.SetValue(i+1,j+1,gp_Pnt(*[float(c[i,j]) for c in cs]))
    def knots(t):
        values,counts=np.unique(t,return_counts=True)
        k=TColStd_Array1OfReal(1,len(values));m=TColStd_Array1OfInteger(1,len(values))
        for i,(value,count) in enumerate(zip(values,counts),1):
            k.SetValue(i,float(value));m.SetValue(i,int(count))
        return k,m
    ku,mu=knots(tx);kv,mv=knots(ty)
    surface=Geom_BSplineSurface(poles,ku,kv,mu,mv,3,3,False,False)
    return Face(BRepBuilderAPI_MakeFace(surface,1e-6).Face())



def rear_end_at_y(y, sign):
    """Registered perimeter intersection used to leave room for the end seat."""
    angle=radians(REAR_YAW)
    yy=max(-39.6,min(39.6,y-REAR_Y))
    for _ in range(4):
        if sign>0:
            x=52.55+5.8*sqrt(max(0,1-(yy/39.6)**2))
        else:
            x=-58.35 if abs(yy)<=27.6 else -46.35-sqrt(max(0,12**2-(abs(yy)-27.6)**2))
        yy=max(-39.6,min(39.6,(y-REAR_Y-x*sin(angle))/cos(angle)))
    return REAR_X+x*cos(angle)-yy*sin(angle)

def front_envelope(length,width,wall=0.0):
    """One continuous skin wraps from the face over both short ends."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace
    from OCP.BRepLib import BRepLib
    us=[-1,-.98,-.96,-.94,-.92,-.90,-.86,-.80,-.74,-.68,-.60,-.50,-.30,0,.30,.50,.60,.68,.74,.80,.86,.90,.92,.94,.96,.98,1]
    vs=[-43,-42,-41,-40.1,-39.6,-39,-38,-37,-36,-34,-31.5,-28,-24,-18,-12,-6,0,6,12,18,24,28,31.5,34,36,37,38,39,39.6,40.1,41,42,43]
    points=[]
    for u in us:
        row=[]
        for y in vs:
            low=-11.9-sqrt(55**2-y*y);high=-28+sqrt(95**2-y*y)
            fade=max(.06,1-(abs(y)/43.2)**4)
            sign=1 if u>=0 else -1;end=high if sign>0 else low
            a=abs(u)
            if a<=.90:
                x=(u/.9)*((high-low-4.8)/2)+(high+low)/2
                z=front_height(x,y)
            else:
                # Rounded lip followed by the inward return seen in the end scan.
                inward=float(PchipInterpolator([.90,.92,.94,.96,.98,1],[2.4,.65,0,.3,1.65,3.4])(a))
                x=end-sign*inward*fade
                original_bottom=end-sign*3.4*fade
                needed=rear_end_at_y(y,sign)+sign*1.1
                correction=sign*max(0,sign*(needed-original_bottom))
                t=(a-.9)/.1
                x+=correction*t*t*(3-2*t)
                tip_z=float(_front_y(abs(y)))-1.9*fade
                bottom=min(_base_back_height(58.35,max(-39.6,min(39.6,y-.45)))+.15,tip_z-8*fade-.3)
                z0=front_height(end-sign*2.4,y)
                z=float(PchipInterpolator([.90,.92,.94,.96,.98,1],[z0,tip_z+1.1*fade,tip_z,tip_z-3.2*fade,tip_z-7.7*fade,bottom])(a))
            t=max(0,min(1,(y-31.5)/8.6));blend=t*t*(3-2*t)
            ear=max(0,float(PchipInterpolator([-30,-16,-13,-11,-9,-7,-5,-3,0,2,10],[0,0,0,.5,2.5,4.1,4.35,3.8,1.0,0,0])(z)))
            yy=y+ear*_ear_x(x)*blend
            row.append((x*length/134*(1-wall/67),yy*width/80.2*(1-wall/40.1),z-wall))
        points.append(row)
    top=surface_from_grid(points,[70*u for u in us],vs)
    surface=BRep_Tool.Surface_s(top.wrapped)
    bounds=surface.Bounds()
    curves=[surface.UIso(bounds[0]),surface.VIso(bounds[3]),surface.UIso(bounds[1]),surface.VIso(bounds[2])]
    sides=[];bottom_edges=[]
    for curve in curves:
        a=curve.Value(curve.FirstParameter());b=curve.Value(curve.LastParameter())
        upper_edge=Edge(BRepBuilderAPI_MakeEdge(curve).Edge())
        lower_edge=Line((a.X(),a.Y(),-30),(b.X(),b.Y(),-30)).edge()
        sides.append(Face.make_surface_from_curves(upper_edge,lower_edge))
        bottom_edges.append(lower_edge)
    bottom=Face(Wire(bottom_edges))
    # Bound trim domains at the transitions into the returning end walls.
    ui=[bounds[0],-63,0,63,bounds[1]]
    vi=[bounds[2],-36,0,36,bounds[3]]
    panels=[Face(BRepBuilderAPI_MakeFace(surface,u0,u1,v0,v1,1e-6).Face()) for u0,u1 in zip(ui,ui[1:]) for v0,v1 in zip(vi,vi[1:])]
    solid=Solid(Shell([*panels,bottom,*sides]))
    BRepLib.OrientClosedSolid_s(solid.wrapped)
    return solid


def board_outline(length=116.0,width=71.0,corner_cut=6.0,clearance=0.0):
    lo,hi,y=2-length/2,2+length/2,width/2
    outline=Polygon((lo,-23),(lo+4,-23),(lo+4,-y+4),(lo+8,-y),(hi-corner_cut,-y),(hi,-y+corner_cut),(hi,y-corner_cut),(hi-corner_cut,y),(lo+8,y),(lo+4,y-4),(lo+4,23),(lo,23),align=None)
    return offset(outline,amount=clearance) if clearance else outline


def portable_solid(shape):
    """Encode the exact surfaces as NURBS so STEP retains trimmed seat faces."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    return Compound.cast(BRepBuilderAPI_NurbsConvert(shape.wrapped,True).Shape()).fix()


def rear_catches(length=116.7,width=79.2,seam_z=-4.3,clearance=0.0):
    """Scan-located rim catches and matching rounded front receiver envelopes."""
    sx,sy=length/116.7,width/79.2
    catches=[]
    # The catch positions differ on the two sides; the flared shoulder has a separate curved return.
    locations=[(x,-38.0) for x in [-50.5,-35.8,-12.7,16.0,52.0]]+[(x,38.0) for x in [-49.0,-19.8,9.0,29.4]]
    for x,y in locations:
        z=seam_z-2.6-clearance
        top=seam_z+1.2+clearance
        catch=Pos(x*sx,y*sy,z)*extrude(RectangleRounded(4.6*sx+2*clearance,2.3*sy+2*clearance,.6+clearance),amount=3.8+2*clearance)
        top_edges=[e for e in catch.edges() if abs(e.center().Z-top)<1e-5]
        catches.append(fillet(top_edges,.35+clearance))
    return catches


def front_shoulder_return(length=134.0,width=80.2,seam_z=-4.3):
    """Lower wrap of the front shoulder, relieved against the asymmetric back skin."""
    sections=[];dz=seam_z+4.3
    # Rear-frame stations: X, lip outline Y, and the front wall at Z=-3.8.
    stations=[(31,39.6,39.43077),(35,39.8,40.24840),(38,40.1,42.29899),(40,40.65,43.31899),(43,41.5,43.87772),(46,42.1,43.91468),(48,42.9,43.92648),(51,43.35,43.90959),(53,43.2,43.88771),(54,41.0,43.86920),(55,38.2,42.94943)]
    for x,edge,top in stations:
        outer=max(top,edge+.55);root=edge-1.5
        under=back_height(x,root)-.25;bottom=min(-4.8,under-.6)
        pts=[(top,-3.8),(outer+.10,-5),(outer,-6.8 if 37<x<54 else bottom+.4),(outer-.25,bottom+.15),(root,bottom),(root,under),(edge+.2,back_height(x,edge)-.25),(max(edge+.2,top-.75),-4.6),(top-.7,-3.8)]
        pts=[(y,z+dz) for y,z in pts]
        wire=Wire([Spline(*pts[:5]).edge(),Line(pts[4],pts[5]).edge(),Spline(*pts[5:]).edge(),Line(pts[-1],pts[0]).edge()])
        sections.append(Plane(origin=(x,0,0),x_dir=(0,1,0),z_dir=(1,0,0))*make_face(wire))
    # Ruled transitions prevent overshoot at the abrupt end of the scanned shoulder.
    lip=loft(sections,ruled=True).fix()
    xs=[25,28,30,35,40,45,48,51,53.6,56,60,65]
    ys=[34,35,36,37,38,38.5,39,40,41,42,43,44,46,50]
    grid=[[(x,y,back_height(min(x,58.35),y,seam_z=seam_z)-.25) for y in ys] for x in xs]
    above=Solid.extrude(surface_from_grid(grid,xs,ys),(0,0,30)).fix()
    outline=Pos(0,0,-30+dz)*extrude(rear_outline(clearance=.2),amount=35)
    lip=(lip-(above&outline).fix()).fix()
    for receiver in rear_catches(seam_z=seam_z,clearance=.2):lip-=receiver
    lip=Pos(REAR_X,REAR_Y,0)*Rot(0,0,REAR_YAW)*lip
    return scale(lip,by=(length/134,width/80.2,1),about=(0,0,0)) if length!=134 or width!=80.2 else lip
