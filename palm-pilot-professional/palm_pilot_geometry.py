"""Analytic exterior construction for the Palm Pilot Professional rebuild."""
from math import sqrt, atan, degrees
from copy import copy
from functools import lru_cache
from nurb import *

FRONT_SLOPE_X = 0.004146
FRONT_SLOPE_Y = 0.0040


def plan_outline(z, top=58.80, corner=3.0, inset=0.0):
    def p(x,y): return (x,y,z)
    left=(-35.821022,-104.899508)
    right=(6.890825,33.500797); rr=92.061589
    distance=sqrt(sum((right[i]-left[i])**2 for i in range(2)))
    lr=distance-rr
    lr+=inset;rr-=inset
    side=40.42-inset
    top-=inset;corner-=inset
    # The two circular chin arcs meet tangentially near the left application key.
    tangent=tuple(left[i]+lr/(lr+rr)*(right[i]-left[i]) for i in range(2))
    yl=lambda x:left[1]+sqrt(lr*lr-(x-left[0])**2)
    yr=lambda x:right[1]-sqrt(rr*rr-(x-right[0])**2)
    a=p(-37.8,yl(-37.8));b=p(*tangent);c=p(38.7,yr(38.7))
    xt=side-corner; yt=top-corner; cm=corner/sqrt(2)
    return Wire([
        Edge.make_line(p(side,-50.65),p(side,yt)),
        Edge.make_three_point_arc(p(side,yt),p(xt+cm,yt+cm),p(xt,top)),
        Edge.make_line(p(xt,top),p(-xt,top)),
        Edge.make_three_point_arc(p(-xt,top),p(-xt-cm,yt+cm),p(-side,yt)),
        Edge.make_line(p(-side,yt),p(-side,-50.35)),
        Edge.make_bezier(p(-side,-50.35),p(-side,-52.12),p(-39.1,yl(-37.8)-1.3*(left[0]+37.8)/sqrt(lr*lr-(-37.8-left[0])**2)),a),
        Edge.make_three_point_arc(a,p(-30,yl(-30)),b),
        Edge.make_three_point_arc(b,p(7,yr(7)),c),
        Edge.make_bezier(c,p(39.45,yr(38.7)+.75*(38.7-right[0])/sqrt(rr*rr-(38.7-right[0])**2)),p(side,-52.0),p(side,-50.65)),
    ])


def side_envelope(z0,z1, rolled=False):
    """The long side walls are large-radius cylinders, extruded along Y."""
    center=8.942;radius=31.284;zc=10.381
    x=lambda z:center+sqrt(radius*radius-(z-zc)**2)
    def p(xx,z): return (xx,-70,z)
    zm=(z0+z1)/2
    if rolled=='bottom':
        r=2.8;cz=z0+r
        cx=center+sqrt((radius-r)**2-(cz-zc)**2)
        tz=zc+radius/(radius-r)*(cz-zc);tx=center+radius/(radius-r)*(cx-center)
        mz=(tz+z0)/2;mx=cx+sqrt(r*r-(mz-cz)**2)
        w=Wire([Edge.make_line(p(-cx,z0),p(cx,z0)),Edge.make_three_point_arc(p(cx,z0),p(mx,mz),p(tx,tz)),Edge.make_three_point_arc(p(tx,tz),p(x((tz+z1)/2),(tz+z1)/2),p(x(z1),z1)),Edge.make_line(p(x(z1),z1),p(-x(z1),z1)),Edge.make_three_point_arc(p(-x(z1),z1),p(-x((tz+z1)/2),(tz+z1)/2),p(-tx,tz)),Edge.make_three_point_arc(p(-tx,tz),p(-mx,mz),p(-cx,z0))])
        return Solid.extrude(Face(w),(0,140,0))
    if rolled:
        r=2.3
        cz=z1-r
        cx=center+sqrt((radius-r)**2-(cz-zc)**2)
        tz=zc+radius/(radius-r)*(cz-zc)
        tx=center+radius/(radius-r)*(cx-center)
        arc_mid_z=(tz+z1)/2
        arc_mid_x=cx+sqrt(r*r-(arc_mid_z-cz)**2)
        w=Wire([
            Edge.make_line(p(-x(z0),z0),p(x(z0),z0)),
            Edge.make_three_point_arc(p(x(z0),z0),p(x((z0+tz)/2),(z0+tz)/2),p(tx,tz)),
            Edge.make_three_point_arc(p(tx,tz),p(arc_mid_x,arc_mid_z),p(cx,z1)),
            Edge.make_line(p(cx,z1),p(-cx,z1)),
            Edge.make_three_point_arc(p(-cx,z1),p(-arc_mid_x,arc_mid_z),p(-tx,tz)),
            Edge.make_three_point_arc(p(-tx,tz),p(-x((z0+tz)/2),(z0+tz)/2),p(-x(z0),z0)),
        ])
        return Solid.extrude(Face(w),(0,140,0))
    w=Wire([
        Edge.make_line(p(-x(z0),z0),p(x(z0),z0)),
        Edge.make_three_point_arc(p(x(z0),z0),p(x(zm),zm),p(x(z1),z1)),
        Edge.make_line(p(x(z1),z1),p(-x(z1),z1)),
        Edge.make_three_point_arc(p(-x(z1),z1),p(-x(zm),zm),p(-x(z0),z0)),
    ])
    return Solid.extrude(Face(w),(0,140,0))


def level_to_scan(shape, rear=False):
    # The preserved reference frame has a small measured front-plane tilt.
    return Rot(degrees(atan(.0085 if rear else FRONT_SLOPE_Y)), -degrees(atan(FRONT_SLOPE_X)), 0)*shape


def coarse_components():
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    builder=BRepOffsetAPI_ThruSections(True,False,1e-6)
    builder.SetMaxDegree(3)
    for z,d in [(16.86,0.0),(17.86,.267949),(18.59205,1.0),(18.86,2.0)]:
        builder.AddWire(plan_outline(z,inset=d).wrapped)
    builder.Build()
    front=extrude(Face(plan_outline(10.65)),amount=16.86-10.65).fuse(Solid(builder.Shape()))
    front=front & side_envelope(10.65,18.86,True)
    rb=BRepOffsetAPI_ThruSections(True,False,1e-6);rb.SetMaxDegree(3)
    for z,d in [(1.8,2.0),(2.06795,1.0),(2.8,.267949),(3.8,0.0)]:
        rb.AddWire(plan_outline(z,59.1,3.0,d).wrapped)
    rb.Build()
    rear=Solid(rb.Shape()).fuse(extrude(Face(plan_outline(3.8,59.1,3.0)),amount=10.2-3.8))
    rear=rear & side_envelope(1.80,10.20,'bottom')
    dock=docking_lip()
    front=front.fuse(dock & Pos(0,-55,15.65)*Box(85,30,10.0))
    rear=rear.fuse(dock & Pos(0,-55,5.2)*Box(85,30,10.0))
    return level_to_scan(front),level_to_scan(rear,True)


def docking_lip():
    """Observed narrower lower lip and its open connector bay."""
    def p(x,z): return (x,-61.0,z)
    w=Wire([
        Edge.make_three_point_arc(p(-36.7,5.3),p(0,3.8),p(36.7,5.3)),
        Edge.make_line(p(36.7,5.3),p(36.7,14.8)),
        Edge.make_three_point_arc(p(36.7,14.8),p(0,16.4),p(-36.7,14.8)),
        Edge.make_line(p(-36.7,14.8),p(-36.7,5.3)),
    ])
    lip=Solid.extrude(Face(w),(0,11.0,0))
    top_edge=[e for e in lip.edges() if e.center().Y < -60.9 and e.center().Z > 14]
    lip=fillet(top_edge,radius=1.8)
    bay=Pos(.4,-58.5,3.3)*Box(25.7,15.0,9.0)
    bay=fillet(bay.edges().filter_by(Axis.Y),radius=.65)
    footprint=Pos(0,-55.5,-1)*extrude(RectangleRounded(73.4,11.0,2.0),amount=25)
    return (lip & footprint)-bay


def rounded_cut(width,height,radius,z,depth,x=0,y=0,angle=0):
    return Pos(x,y,z)*Rot(0,0,angle)*extrude(RectangleRounded(width,height,radius),amount=depth)


def button_well(x,y):
    # This observed bowl is a circular meridian, not a hard cylindrical counterbore.
    r=2.5;cx=6.46;cz=16.36
    p0=(0,0,16.45);p1=(4.25,0,16.45)
    a=(4.25,0,cz+sqrt(r*r-(4.25-cx)**2));b=(5.45,0,cz+sqrt(r*r-(5.45-cx)**2));c=(cx,0,cz+r)
    w=Wire([Edge.make_line(p0,p1),Edge.make_line(p1,a),Edge.make_three_point_arc(a,b,c),Edge.make_line(c,(cx,0,22)),Edge.make_line((cx,0,22),(0,0,22)),Edge.make_line((0,0,22),p0)])
    return Pos(x,y,0)*revolve(Face(w),axis=Axis.Z)


def _scroll_outline(z,xc,half,inner,outer,radius,direction=1,inner_roll=.95,outer_roll=1.15):
    """An outward circular bow, tangent rolled ends and a flatter facing edge."""
    from math import atan2,cos,sin,pi
    ri=min(inner_roll,half*.48,(outer-inner)*.4)
    ro=min(outer_roll,half*.48,(outer-inner)*.4)
    cy=outer-radius
    fc=(half-ro,cy+sqrt((radius-ro)**2-(half-ro)**2))
    phi=atan2(fc[1]-cy,fc[0])
    tangent=(radius*cos(phi),cy+radius*sin(phi))
    def p(x,y):return (xc+x,direction*y,z)
    def arc(c,r,a,b):
        return Edge.make_three_point_arc(p(c[0]+r*cos(a),c[1]+r*sin(a)),p(c[0]+r*cos((a+b)/2),c[1]+r*sin((a+b)/2)),p(c[0]+r*cos(b),c[1]+r*sin(b)))
    e=[arc((0,cy),radius,pi-phi,phi),arc(fc,ro,phi,0),Edge.make_line(p(half,fc[1]),p(half,inner+ri)),arc((half-ri,inner+ri),ri,0,-pi/2),Edge.make_line(p(half-ri,inner),p(-half+ri,inner)),arc((-half+ri,inner+ri),ri,-pi/2,-pi),Edge.make_line(p(-half,inner+ri),p(-half,fc[1])),arc((-fc[0],fc[1]),ro,pi,pi-phi)]
    wire=Wire(e);wire._profile_edges=e
    return wire


def _scroll_ellipse(z,xc,yc,a,b,direction=1):
    from math import cos,sin,tan,pi
    angles=[135,45,22.5,-22.5,-45,-135,-157.5,-202.5,-225]
    edges=[]
    for t0,t1 in zip(angles,angles[1:]):
        t0*=pi/180;t1*=pi/180;k=4/3*tan((t1-t0)/4)
        p0=(xc+a*cos(t0),yc+b*sin(t0),z);p3=(xc+a*cos(t1),yc+b*sin(t1),z)
        p1=(p0[0]-k*a*sin(t0),p0[1]+k*b*cos(t0),z)
        p2=(p3[0]+k*a*sin(t1),p3[1]-k*b*cos(t1),z)
        edges.append(Edge.make_bezier(*[(p[0],direction*p[1],p[2]) for p in [p0,p1,p2,p3]]))
    wire=Wire(edges);wire._profile_edges=edges
    return wire


def _front_scan_datum(shape):
    return shape.transform_geometry(Matrix([[1,0,0,0],[0,1,0,0],[FRONT_SLOPE_X,FRONT_SLOPE_Y,1,0],[0,0,0,1]]))


def scroll_key(label):
    """Measured cap contours transition into the shallow crown; hidden stem is nominal."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    up=label=='Scroll up';direction=1 if up else -1
    if up:
        low=[(18.65,1.06,4.58,-44.94,-40.84,13.0),(18.9,1.06,4.4763,-44.8575,-40.9769,12.945),(19.0,1.055,4.3938,-44.8187,-41.0617,13.045),(19.2,1.05,4.2881,-44.7756,-41.1509,12.95),(19.4,1.035,4.1663,-44.6893,-41.2346,12.49),(19.6,.988,3.8817,-44.5791,-41.4038,11.401)]
        high=[(19.8,.9542,-43.0158,3.0944,1.2865),(19.95,.9577,-42.9784,2.0557,.8647),(20.0,.9338,-42.9779,1.5576,.6513),(20.055,.936,-42.998,.442,.185)]
    else:
        low=[(18.65,1.09,4.51,48.66,52.65,13.0),(18.9,1.096,4.3842,48.7663,52.5439,12.762),(19.0,1.093,4.3248,48.8429,52.5254,13.047),(19.2,1.078,4.2357,48.9248,52.4953,12.824),(19.4,1.082,4.0955,49.0557,52.4426,12.14),(19.6,1.057,3.7486,49.2792,52.2997,10.435)]
        high=[(19.8,1.0875,-50.7701,2.7355,1.1412),(19.95,1.1103,-50.772,1.4931,.6376),(20.0,1.1258,-50.7209,.7044,.2856),(20.005,1.077,-50.768,.222,.093)]
    profiles=[_scroll_outline(17.75,*low[0][1:],direction=direction)]
    profiles.extend(_scroll_outline(*row,direction=direction) for row in low)
    profiles.extend(_scroll_ellipse(*row) if up else _scroll_ellipse(row[0],row[1],-row[2],row[3],row[4],direction=-1) for row in high)
    # Corresponding cubic edges and shape-preserving interpolation avoid folded loft crowns.
    # The 0.03 mm axial patches stay well below scan noise while retaining the measured rim.
    import numpy as np
    from scipy.interpolate import PchipInterpolator
    levels=[];controls=[]
    for wire in profiles:
        edges=[]
        for edge in wire._profile_edges:
            p=np.array([tuple(edge.position_at(t)) for t in [0,1/3,2/3,1.]])
            rhs=p[1:3]-np.array([(8*p[0]+p[3])/27,(p[0]+8*p[3])/27])
            c=np.linalg.solve(np.array([[4/9,2/9],[2/9,4/9]]),rhs)
            edges.append([p[0],c[0],c[1],p[3]])
        levels.append(float(edges[0][0][2]));controls.append(edges)
    interpolate=PchipInterpolator(levels,np.array(controls),axis=0)
    maker=BRepOffsetAPI_ThruSections(True,True,1e-6);maker.CheckCompatibility(False)
    count=int(np.ceil((levels[-1]-levels[0])/.03))
    for z in np.linspace(levels[0],levels[-1],count+1):
        points=interpolate(z);points[:,:,2]=z
        ring=Wire([Edge.make_bezier(*[tuple(p) for p in edge]) for edge in points])
        maker.AddWire(ring.wrapped)
    maker.Build();cap=Solid(maker.Shape())
    base=Face(_scroll_outline(0,*low[0][1:],direction=direction))
    well_profiles=[]
    for z,gap in [(17.5,.12),(18.60,.12),(18.74,.20),(18.90,.58),(19.4,1.)]:
        well_profiles.append(Pos(0,0,z)*offset(base,amount=gap))
    well=loft(well_profiles)
    return _front_scan_datum(cap),_front_scan_datum(well)


def dock_side_sockets():
    """Paired observed seam-crossing mouths; the shallow blind closure is nominal."""
    x=35.0
    rows=[(8.2,-57.301,-54.934),(8.5,-57.332,-54.930),(9.0,-57.354,-54.969),(9.5,-57.486,-54.773),(10.0,-57.523,-54.696),(10.5,-57.372,-54.999),(11.0,-57.293,-55.041),(11.5,-57.230,-55.036)]
    def p(y,z):return (x,y,z)
    # Smooth bounded sides retain the observed seam-level flare.
    def side(k):
        pts=[(z,row[k]) for row in rows for z in [row[0]]]
        curves=_lip_edges(0,pts)
        # _lip_edges stores (0,z,y); cyclically permute to the YZ socket plane.
        return [e.transform_geometry(Matrix([[1,0,0,x],[0,0,1,0],[0,1,0,0],[0,0,0,1]])) for e in curves]
    left=side(1);right=side(2)
    upper=Edge.make_bezier(p(-57.230,11.5),p(-57.16,12.14),p(-55.12,12.14),p(-55.036,11.5))
    lower=Edge.make_bezier(p(-54.934,8.2),p(-54.99,7.4613),p(-57.24,7.4613),p(-57.301,8.2))
    wire=Wire([*left,upper,*[e.reversed() for e in right[::-1]],lower])
    tool=Solid.extrude(Face(wire),(4.,0,0))
    return tool.fuse(mirror(tool,about=Plane.YZ))


def front_features(front,screen_width=59.623,screen_height=80.551,button_width=8.5):
    # Work in the levelled front datum; each separate insert follows that same frame.
    pose=Rot(degrees(atan(FRONT_SLOPE_Y)),-degrees(atan(FRONT_SLOPE_X)),0)
    front=pose.inverse()*front
    center=(1.04,6.875);angle=.19
    low=rounded_cut(screen_width,screen_height,1.8,16.85,1.17,*center,angle)
    rings=[]
    for z,grow in [(18.02,0),(18.40,.15),(18.70,.48),(19.3,1.05)]:
        rings.append(Pos(*center,z)*Rot(0,0,angle)*RectangleRounded(screen_width+2*grow,screen_height+2*grow,1.8+grow))
    opening=low.fuse(loft(rings))
    front=front-opening
    display=rounded_cut(screen_width-.16,screen_height-.16,1.72,16.92,.2508,*center,angle)
    pieces=[('Display',pose*display)]
    specs=[(-25.029,-45.228,11.567,6.961),(-11.416,-45.215,11.581,7.006),(13.596,-45.184,11.692,6.955),(27.186,-45.165,11.642,6.937)]
    for i,(x,y,zc,radius) in enumerate(specs,1):
        front=front-button_well(x,y)
        cap_zc=zc-FRONT_SLOPE_X*x-FRONT_SLOPE_Y*y
        dome=Pos(x,y,cap_zc)*Sphere(radius)
        stem=Pos(x,y,16.46)*Cylinder(button_width/2,4,align=(Align.CENTER,Align.CENTER,Align.MIN))
        cap=dome & stem
        # Remove only the singular spherical pole that OCCT writes as a zero-area STL triangle.
        cap_top=cap_zc+radius-.0001
        cap=cap & (Pos(x,y,(16.46+cap_top)/2)*Box(12,12,cap_top-16.46))
        pieces.append((f'Application button {i}',pose*cap))
    for label in ['Scroll up','Scroll down']:
        cap,well=scroll_key(label)
        front=front-(pose.inverse()*well)
        pieces.append((label,cap))
    power=rounded_cut(5.25,6.75,.6,17.16,1.10,-36.55,-45.57)
    front=front-rounded_cut(9.0,7.10,.7,16.95,5,-38.28,-45.57)
    power=fillet(power.faces().sort_by(Axis.Z)[-1].edges(),radius=.3)
    pieces.append(('Power button',pose*power))
    return pose*front,pieces


def _ordinate(points, value):
    from bisect import bisect_right
    slopes=[]
    secants=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(points,points[1:])]
    slopes.append(secants[0])
    for i in range(1,len(points)-1):
        h0=points[i][0]-points[i-1][0];h1=points[i+1][0]-points[i][0]
        a,b=secants[i-1],secants[i]
        slopes.append(0. if a*b<=0 else 3*(h0+h1)/((2*h1+h0)/a+(h1+2*h0)/b))
    slopes.append(secants[-1])
    i=min(len(points)-2,max(0,bisect_right([p[0] for p in points],value)-1))
    u0,v0=points[i];u1,v1=points[i+1];h=u1-u0;t=(value-u0)/h
    return (2*t**3-3*t*t+1)*v0+(t**3-2*t*t+t)*h*slopes[i]+(-2*t**3+3*t*t)*v1+(t**3-t*t)*h*slopes[i+1]


def _lip_edges(x, points):
    secants=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(points,points[1:])]
    slopes=[0.]
    for i in range(1,len(points)-1):
        h0=points[i][0]-points[i-1][0];h1=points[i+1][0]-points[i][0]
        a,b=secants[i-1],secants[i]
        slopes.append(0. if a*b<=0 else 3*(h0+h1)/((2*h1+h0)/a+(h1+2*h0)/b))
    slopes.append(secants[-1])
    result=[]
    for i,((y0,z0),(y1,z1)) in enumerate(zip(points,points[1:])):
        h=(y1-y0)/3
        result.append(Edge.make_bezier((x,y0,z0),(x,y0+h,z0+h*slopes[i]),(x,y1-h,z1-h*slopes[i+1]),(x,y1,z1)))
    return result


def _keyway_profile(x,yc,low,high,nose_radius,lower,upper):
    ys=[35.,38.,40.,45.,50.,55.,57.,58.,62.]
    lower_points=[(yc,low),*zip(ys,lower)]
    upper_points=[(yc,high),*zip(ys,upper)]
    lo=_lip_edges(x,lower_points);hi=_lip_edges(x,upper_points)
    zc=(low+high)/2;rz=(high-low)/2;k=.5522847498307936
    nose=(x,yc-nose_radius,zc)
    bottom=Edge.make_bezier((x,yc,low),(x,yc-k*nose_radius,low),(x,yc-nose_radius,zc-k*rz),nose)
    top=Edge.make_bezier(nose,(x,yc-nose_radius,zc+k*rz),(x,yc-k*nose_radius,high),(x,yc,high))
    return Wire([*hi,Edge.make_line((x,62.,upper[-1]),(x,62.,lower[-1])),*[e.reversed() for e in lo[::-1]],bottom,top])


def _measured_keyway():
    """Measured outer lips, with a small nominal relief for the finished grip rib."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    data=[
        (38.10,34.0546,5.7000,8.0026,1.0276,[5.5350,5.5350,5.5350,5.5300,5.5050,5.3997,5.3058,5.0782,3.4],[8.0950,8.1933,8.2277,8.3226,8.4018,8.4554,8.4444,8.4258,10.0]),
        (39.00,34.0546,5.7000,8.0026,1.0276,[5.5350,5.5350,5.5350,5.5300,5.5050,5.3997,5.3058,5.0782,3.4],[8.0950,8.1933,8.2277,8.3226,8.4018,8.4554,8.4444,8.4258,10.0]),
        (39.25,33.8636,5.7200,7.9608,1.0273,[5.5650,5.5600,5.5500,5.5150,5.4550,5.3634,5.2612,4.95,3.3],[8.0904,8.1934,8.2260,8.3204,8.3987,8.4579,8.4411,8.4453,10.0]),
        (39.50,33.7431,5.7831,7.8997,1.0433,[5.6100,5.5297,5.4959,5.4249,5.3439,5.2376,5.0581,4.8,3.2],[8.0586,8.2018,8.2395,8.3353,8.4139,8.4733,8.4580,8.5177,10.2]),
        (39.75,33.62,5.3031,7.9397,1.15,[5.1735,4.9087,4.90,4.85,4.80,4.75,4.70,4.4,3.0],[8.0915,8.2544,8.2969,8.4118,8.4778,8.5231,8.5216,8.7348,10.4]),
        (40.10,33.45,4.60,8.1697,1.30,[4.5,4.3,4.2,4.1,4.,3.9,3.8,3.4,2.5],[8.3747,8.5448,8.5890,8.7101,8.7519,8.7641,8.8010,9.0,10.6]),
        (42.00,33.45,4.60,8.1697,1.30,[4.5,4.3,4.2,4.1,4.,3.9,3.8,3.4,2.5],[8.3747,8.5448,8.5890,8.7101,8.7519,8.7641,8.8010,9.0,10.6]),
    ]
    maker=BRepOffsetAPI_ThruSections(True,True,1e-6)
    for values in data:maker.AddWire(_keyway_profile(*values).wrapped)
    maker.Build()
    return Solid(maker.Shape())


def _mouth_profile(y,rx,top,bottom,right,r300,r315):
    cx,cz=36.0517,6.8262;k=.5522847498307936
    p=lambda dx,dz:(cx+dx,y,cz+dz)
    lower=[(0.,-bottom),(.5*r300,-.8660254037844386*r300),(.7071067811865475*r315,-.7071067811865475*r315),(4.3,0.)]
    lower_edges=[Pos(cx,y,cz)*Rot(0,0,-90)*e for e in _lip_edges(0,lower)]
    return Wire([
        Edge.make_bezier(p(right,0),p(right,k*top),p(k*right,top),p(0,top)),
        Edge.make_bezier(p(0,top),p(-k*rx,top),p(-rx,k*top),p(-rx,0)),
        Edge.make_bezier(p(-rx,0),p(-rx,-k*bottom),p(-k*rx,-bottom),p(0,-bottom)),
        *lower_edges,Edge.make_line(p(4.3,0),p(right,0)),
    ])


def _measured_mouth(radius):
    """Local rounded flare, bounded below by the nominal running bore."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    # Bottom continuation after 58.5 clears outside the disappearing rear lip.
    data=[(56.5,radius-.05,radius-.05,radius-.05),(57.05,2.6480,2.5594,2.5816),(57.55,2.6933,2.5782,2.5945),(58.05,2.7558,2.6209,2.6925),(58.55,2.8943,2.7072,3.1751),(58.75,3.0184,2.7606,3.5),(58.95,3.5774,2.9268,4.0),(59.2,4.2,3.5,5.0),(60.5,5.,5.,6.)]
    radial=[(56.5,radius-.05,radius-.05),(57.05,2.635609,2.685548),(57.55,2.704123,2.758278),(58.05,2.755918,2.813955),(58.25,2.802712,2.884209),(58.45,2.903102,3.038441),(58.55,2.994348,3.244255),(58.65,3.162057,3.8),(58.75,3.7,4.2),(59.2,4.5,5.1),(60.5,5.2,5.5)]
    maker=BRepOffsetAPI_ThruSections(True,True,1e-6)
    for i in range(81):
        y=56.5+.05*i
        values=[_ordinate([(s[0],s[j]) for s in data],y) for j in (1,2,3)]
        r300,r315=[_ordinate([(s[0],s[j]) for s in radial],y) for j in (1,2)]
        maker.AddWire(_mouth_profile(y,*values,radius-.03,r300,r315).wrapped)
    maker.Build()
    return Solid(maker.Shape())


def _rear_mouth_roll():
    """Observed thin rear lip rolls away before the front lip at the mouth."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    data=[(58.2,2.70,1.72),(58.3,2.845,1.60),(58.4,2.98,1.51),(58.5,3.16,1.40),(58.55,3.245,1.28),(58.6,3.37,1.18),(58.65,3.58,1.08),(58.7,4.0,.95),(58.8,4.5,.8),(59.2,5.,.6)]
    maker=BRepOffsetAPI_ThruSections(True,True,1e-6)
    for i in range(21):
        y=58.2+.05*i
        base,r=[_ordinate([(s[0],s[j]) for s in data],y) for j in (1,2)]
        p=lambda x,z:(x,y,z)
        lower=[(35.8,base-1.2),(36.5,base-.2),(37.,base),(37.2,base)]
        edges=[Pos(0,y,0)*Rot(0,0,-90)*e for e in _lip_edges(0,lower)]
        wire=Wire([Edge.make_line(p(35.8,6.5),p(37.2,6.5)),Edge.make_line(p(37.2,6.5),p(37.2,base+2*r)),Edge.make_three_point_arc(p(37.2,base+2*r),p(37.2+r,base+r),p(37.2,base)),*[e.reversed() for e in edges[::-1]],Edge.make_line(p(35.8,base-1.2),p(35.8,6.5))])
        maker.AddWire(wire.wrapped)
    maker.Build()
    keep=Solid(maker.Shape())
    region=Pos(35.8,58.2,-2)*Box(6.2,1.,8.2,align=(Align.MIN,Align.MIN,Align.MIN))
    return region-keep


def stylus_passage(shape, shaft_diameter=5.180704, bore_allowance=.2):
    """Use the ungrooved master tip and straight extraction envelope, not groove replicas."""
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path
    # The viewer loads parts outside package context; anchor the unchanged master to this project.
    master_path=Path(__file__).resolve().parent/'parts/palm_pilot_stylus.py'
    spec=spec_from_file_location('_palm_pilot_stylus_master',master_path)
    master=module_from_spec(spec)
    spec.loader.exec_module(master)
    _round_tip=master._round_tip
    radius=shaft_diameter/2;clearance=bore_allowance/2;bore_radius=radius+clearance
    # Offset the smooth insertion envelope, never the annular grip grooves.
    tip=offset(_round_tip(radius,15.),amount=clearance+.0001,kind=Kind.ARC)
    limit=Pos(0,0,-1)*Cylinder(bore_radius,18,align=(Align.CENTER,Align.CENTER,Align.MIN))
    tip=tip & limit
    bore=Pos(0,0,15.)*Cylinder(bore_radius,95.,align=(Align.CENTER,Align.CENTER,Align.MIN))
    passage=Pos(36.0517,-48.053,6.8262)*Rot(-90,0,0)*tip.fuse(bore)
    mouth=_measured_mouth(bore_radius)
    slot=_measured_keyway()
    return shape-passage-mouth-slot-_rear_mouth_roll()


@lru_cache(maxsize=8)
def _detailed_components(screen_width=59.623,screen_height=80.551,button_width=8.5,shaft_diameter=5.180704,bore_allowance=.2):
    front,rear=coarse_components()
    # Only the dock seam has an observed recessed back wall; retain the separate casing halves.
    backing=Pos(0,-56.5,9.8)*Box(73.1,7.0,2.4)
    backing=backing & level_to_scan(docking_lip(),rear=True)
    rear=rear.fuse(backing-front)
    sockets=dock_side_sockets()
    front=front-sockets
    rear=rear-sockets
    def cp(y,z):return (-12.45,y,z)
    cw=Wire([Edge.make_line(cp(-62,-3),cp(-62,7.9)),Edge.make_line(cp(-62,7.9),cp(-59,7.9)),Edge.make_bezier(cp(-59,7.9),cp(-58.5,7.9),cp(-58.5,7.34),cp(-57.9,7.34)),Edge.make_line(cp(-57.9,7.34),cp(-51.5,7.34)),Edge.make_line(cp(-51.5,7.34),cp(-51.5,-3)),Edge.make_line(cp(-51.5,-3),cp(-62,-3))])
    connector=Solid.extrude(Face(cw),(25.7,0,0))
    rear=rear-connector
    front,inserts=front_features(front,screen_width,screen_height,button_width)
    front=stylus_passage(front,shaft_diameter,bore_allowance)
    rear=stylus_passage(rear,shaft_diameter,bore_allowance)
    return [('Front casing',front),*refine_rear(rear),*inserts]

"""Observed rear details for the Palm Pilot exterior reconstruction."""
from build123d import *


def _datum(shape):
    """Keep the independently measured rear slope in the fixed scan frame."""
    return shape.transform_geometry(Matrix([[1, 0, 0, 0], [0, 1, 0, 0], [.004146, .0085, 1, 0], [0, 0, 0, 1]]))


def _rounded_prism(width, height, radius, depth, x, y, z):
    return Pos(x, y, z) * extrude(RectangleRounded(width, height, radius), amount=depth)


def _cover():
    # The broad back of the upper cover has a measured longitudinal bulge.
    points = [(-27.05, 34.1, 2.18), (-27.05, 35.0, 2.16), (-27.05, 40.0, 1.74), (-27.05, 45.0, 1.34), (-27.05, 50.0, .97), (-27.05, 55.0, .64), (-27.05, 56.3, .57)]
    lower = Spline(*points)
    end = ThreePointArc(points[-1], (-27.05, 57.65, .93), (-27.05, 58.45, 2.3))
    edges = [lower, end, Line((-27.05, 58.45, 2.3), (-27.05, 58.45, 3.5)), Line((-27.05, 58.45, 3.5), (-27.05, 34.1, 3.5)), Line((-27.05, 34.1, 3.5), points[0])]
    skin = Solid.extrude(Face(Wire(edges)), (55.7, 0, 0))
    footprint = _rounded_prism(55.7, 24.35, 1.2, 5.0, .8, 46.275, 0.0)
    skin = skin & footprint
    # Soften only the side intersections of the cover and its longitudinal face.
    side_edges = [edge for edge in skin.edges() if edge.length > 15 and abs(edge.center().X - .8) > 26 and edge.center().Z < 2.5]
    if side_edges:
        skin = fillet(side_edges, radius=.65)
    return skin


def battery_outline():
    """Observed rear seam flares around the rolled left edge."""
    def p(x,y):return (x,y,-3.)
    return Wire([Line(p(-46,-42.1),p(-39,-42.1)),Bezier(p(-39,-42.1),p(-37,-42.1),p(-37,-40.15),p(-34.5,-40.15)),Line(p(-34.5,-40.15),p(11.8,-40.15)),ThreePointArc(p(11.8,-40.15),p(11.8+1/sqrt(2),-39.15-1/sqrt(2)),p(12.8,-39.15)),Line(p(12.8,-39.15),p(12.8,-15.8)),ThreePointArc(p(12.8,-15.8),p(11.8+1/sqrt(2),-15.8+1/sqrt(2)),p(11.8,-14.8)),Line(p(11.8,-14.8),p(-34.5,-14.8)),Bezier(p(-34.5,-14.8),p(-37,-14.8),p(-37,-13.3),p(-39,-13.3)),Line(p(-39,-13.3),p(-46,-13.3)),Line(p(-46,-13.3),p(-46,-42.1))])


def thumb_dish():
    # The shallow D-shaped finger purchase is observed. It does not imply a latch.
    arc=Edge.make_ellipse(7.8,6.2,plane=Plane(origin=(-2.6,-27.6,-3)),start_angle=-90,end_angle=90)
    edge=Edge.make_line(arc.end_point(),arc.start_point())
    tool=extrude(Face(Wire([arc,edge])),amount=5.28)
    upper=[e for e in tool.edges() if e.center().Z>2.27 and e.length>15]
    tool=fillet(upper,radius=1.0)
    return _datum(tool)


def refine_rear(rear):
    """Partition the observed exterior into two sliding doors and fixed details."""
    rear=rear.fuse(_cover())
    label=_datum(_rounded_prism(40.5,20.5,.45,.75,-14.05,-5.15,1.2))
    rear=rear-label
    reset=Pos(-26.329,-9.249,-3.0)*Cylinder(2.1,6.86,align=(Align.CENTER,Align.CENTER,Align.MIN))
    rear=rear-reset-thumb_dish()
    for x,y in [(-33.,-56.),(32.,-55.8)]:
        rear=rear-Pos(x,y,-2)*Cylinder(2.15,8.15,align=(Align.CENTER,Align.CENTER,Align.MIN))
    # The backing thickness and smooth slide seats are nominal hidden geometry.
    backing=_datum(Pos(0,0,-3)*Box(110,160,7.4,align=(Align.CENTER,Align.CENTER,Align.MIN)))
    memory_plan=_rounded_prism(67.6,65.,1.,15.,-2.2,43.5,-3.)
    battery_face=Face(battery_outline())
    battery_plan=extrude(battery_face,amount=15)
    memory=rear & memory_plan & backing
    battery_backing=_datum(Pos(0,0,-3)*Box(110,160,7.85,align=(Align.CENTER,Align.CENTER,Align.MIN)))
    battery=rear & battery_plan & battery_backing
    memory_seat=_datum(_rounded_prism(68.,85.,1.2,7.6,-2.2,53.30,-3.))
    battery_seat=_datum(extrude(offset(battery_face,amount=.2),amount=8.05))
    rear=rear-memory_seat-battery_seat
    pieces=[('Memory cover',memory),('Battery cover',battery)]
    pad=Pos(14.406,-1.920,.95)*Cylinder(6.84,1.55,align=(Align.CENTER,Align.CENTER,Align.MIN))
    pad=fillet([e for e in pad.edges() if abs(e.center().Z-.95)<.001],radius=.4)
    pieces.append(('Round rear pad',pad))
    for name,x,y in [('Upper left rear foot',-32.1,52.3),('Upper right rear foot',34.6,52.3),('Lower left rear foot',-32.1,-45.3),('Lower right rear foot',34.6,-45.3)]:
        foot=_rounded_prism(2.65,6.8,.88,1.15,x,y,1.07)
        foot=fillet([e for e in foot.edges() if abs(e.center().Z-1.07)<.001],radius=.38)
        pieces.append((name,_datum(foot)))
    for label,piece in pieces[2:]:
        rear=rear-piece
        memory=memory-piece
        battery=battery-piece
    traveling_foot=next(piece for name,piece in pieces if name=='Upper left rear foot')
    memory=memory.fuse(traveling_foot)
    pieces=[item for item in pieces if item[0]!='Upper left rear foot']
    pieces[:2]=[('Memory cover',memory),('Battery cover',battery)]
    result=[('Rear casing',rear),*pieces]
    for label,piece in result:
        if not piece.is_valid or len(piece.solids())!=1 or piece.volume<=0:
            raise ValueError(f'{label}: valid={piece.is_valid}, solids={len(piece.solids())}, volume={piece.volume}')
    return result


def detailed_components(screen_width=59.623,screen_height=80.551,button_width=8.5,shaft_diameter=5.180704,bore_allowance=.2):
    """Share the closed construction between exports, with fresh shape wrappers."""
    return [(name,copy(shape)) for name,shape in _detailed_components(screen_width,screen_height,button_width,shaft_diameter,bore_allowance)]
