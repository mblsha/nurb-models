"""Measured circular shaft, rounded tip and extraction rib with eight molded grooves."""
from nurb import *
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections


def _round_tip(radius, length):
    stations=[(0,.02),(.1,.387),(.25,.602),(.5,.783),(.75,.895),(1.,.964),(1.36,1.050),(2.,1.201),(3.,1.450),(4.,1.654),(5.36,1.877),(7.5,2.173),(10.36,2.418),(12.86,2.540),(15.,2.590352)]
    stations=[(z*length/15.,r*radius/2.590352) for z,r in stations]
    # Shape-preserving derivatives keep every axial interval monotone.
    secants=[(r1-r0)/(z1-z0) for (z0,r0),(z1,r1) in zip(stations,stations[1:])]
    slopes=[6.0*radius/2.590352*15./length]
    for i in range(1,len(stations)-1):
        h0=stations[i][0]-stations[i-1][0];h1=stations[i+1][0]-stations[i][0]
        a,b=secants[i-1],secants[i]
        slopes.append((3*(h0+h1))/((2*h1+h0)/a+(h1+2*h0)/b))
    slopes.append(0.)
    curves=[]
    for i,((z0,r0),(z1,r1)) in enumerate(zip(stations,stations[1:])):
        h=(z1-z0)/3
        curves.append(Edge.make_bezier((r0,0,z0),(r0+h*slopes[i],0,z0+h),(r1-h*slopes[i+1],0,z1-h),(r1,0,z1)))
    wire=Wire([Edge.make_line((0,0,0),(stations[0][1],0,0)),*curves,Edge.make_line((radius,0,length),(0,0,length)),Edge.make_line((0,0,length),(0,0,0))])
    return revolve(Face(wire),axis=Axis.Z)


def _rib_section(z,xmax,width,neck=1.,root=1.7):
    # The two sides share one averaged measured half-width profile.
    half=width/2
    neck_x=min(2.5,root+(xmax-root)*.32)
    shoulder=max(neck_x+.06,xmax-.8)
    near=max(shoulder+.02,xmax-.25)
    if xmax-root<1.2:
        neck_x=root+.24*(xmax-root);shoulder=root+.58*(xmax-root);near=root+.84*(xmax-root)
    pts=[(root,-min(neck,.7*half),z),(neck_x,-min(neck,half),z),(shoulder,-half,z),(near,-half*.70,z),(xmax,0,z)]
    lower=Edge.make_spline(pts,tangents=[(1,0,0),(0,1,0)])
    upper=Edge.make_spline([(x,-y,zz) for x,y,zz in pts[::-1]],tangents=[(0,1,0),(-1,0,0)])
    return Wire([lower,upper,Edge.make_line((root,-pts[0][1],z),pts[0])])


def _grip_rib_base(length):
    stations=[(81.35,2.50,.10,.05,1.7),(81.5,2.794,.90,.45,1.7),(81.864,3.970,1.25,.70,1.7),(82.,4.030,1.48,.80,1.7),(83.,4.113,2.13,1.04,1.7),(85.,4.138,2.145,1.035,1.7),(90.,4.316,2.20,1.01,1.7),(95.,4.632,2.31,1.01,1.7),(100.,5.107,2.49,.99,1.7),(103.,5.353,2.53,.98,1.7),(104.,5.616,2.67,.95,1.7),(105.,5.634,2.63,.97,1.7),(106.,5.913,2.80,.97,1.7),(106.5,5.965,2.71,.965,1.7),(107.,5.608,2.055,.87,1.2),(107.2,4.292,1.456,.68,.8),(107.3,3.357,.98,.36,1.09),(107.35,2.60,.42,.14,1.35),(107.368,2.10,.04,.02,1.60)]
    loft_builder=BRepOffsetAPI_ThruSections(True,False,1e-6)
    loft_builder.SetMaxDegree(3)
    for z,xmax,width,neck,root in stations:
        loft_builder.AddWire(_rib_section(z+length-107.368,xmax,width,neck,root).wrapped)
    loft_builder.Build()
    return Solid(loft_builder.Shape())


def _grip_rib(length):
    # A local ruled patch bounds interpolation error and leaves the crown unchanged.
    from bisect import bisect_right
    profile=[(95.0, 4.632), (96.0, 4.727599), (96.15, 4.741689), (96.375, 4.737263), (96.6, 4.716285), (96.75, 4.699006), (96.975, 4.693267), (97.2, 4.73278), (97.35, 4.782685), (97.575, 4.851714), (97.8, 4.881797), (97.95, 4.901376), (98.025, 4.911166), (98.175, 4.928785), (98.4, 4.921978), (98.625, 4.900808), (98.775, 4.892043), (99.0, 4.895037), (99.225, 4.934929), (99.375, 4.986224), (99.6, 5.059493), (99.825, 5.094775), (99.975, 5.114197), (100.05, 5.123907), (100.2, 5.13367), (100.425, 5.13595), (100.65, 5.118918), (100.8, 5.114806), (101.025, 5.124794), (101.25, 5.170617), (101.4, 5.221489), (101.625, 5.284487), (101.85, 5.330974), (102.0, 5.354776), (102.075, 5.36644), (102.225, 5.377356), (102.45, 5.384793), (102.675, 5.376286), (102.825, 5.365689), (103.05, 5.377274), (103.275, 5.428037), (103.425, 5.484382), (103.65, 5.556847), (103.875, 5.607439), (104.025, 5.630232), (104.1, 5.638539), (104.25, 5.653349), (104.475, 5.658269), (104.7, 5.646681), (104.85, 5.635904), (105.075, 5.661912), (105.3, 5.72393), (105.45, 5.775291), (105.675, 5.844469), (105.9, 5.894907), (106.0, 5.913)]
    secants=[(x1-x0)/(z1-z0) for (z0,x0),(z1,x1) in zip(profile,profile[1:])]
    slopes=[secants[0]]
    for i in range(1,len(profile)-1):
        h0=profile[i][0]-profile[i-1][0];h1=profile[i+1][0]-profile[i][0]
        a,b=secants[i-1],secants[i]
        slopes.append(0. if a*b<=0 else 3*(h0+h1)/((2*h1+h0)/a+(h1+2*h0)/b))
    slopes.append(secants[-1])
    def xmax_at(z):
        i=min(len(profile)-2,max(0,bisect_right([p[0] for p in profile],z)-1))
        z0,x0=profile[i];z1,x1=profile[i+1];h=z1-z0;t=(z-z0)/h
        return (2*t**3-3*t*t+1)*x0+(t**3-2*t*t+t)*h*slopes[i]+(-2*t**3+3*t*t)*x1+(t**3-t*t)*h*slopes[i+1]
    dimensions=[(95.,2.31,1.01),(100.,2.49,.99),(103.,2.53,.98),(104.,2.67,.95),(105.,2.63,.97),(106.,2.80,.97)]
    patch_builder=BRepOffsetAPI_ThruSections(True,True,1e-6)
    for j in range(111):
        z=95.+.1*j
        for low,high in zip(dimensions,dimensions[1:]):
            if low[0]<=z<=high[0]:
                t=(z-low[0])/(high[0]-low[0]);width=low[1]+t*(high[1]-low[1]);neck=low[2]+t*(high[2]-low[2])
                break
        patch_builder.AddWire(_rib_section(z+length-107.368,xmax_at(z),width,neck,1.7).wrapped)
    patch_builder.Build()
    patch=Solid(patch_builder.Shape())
    original=_grip_rib_base(length)
    ends=original-Pos(0,0,95.+length-107.368)*Box(20,10,11,align=(Align.CENTER,Align.CENTER,Align.MIN))
    rib=patch.fuse(*ends.solids())
    if not rib.is_valid or len(rib.solids())!=1:
        raise ValueError('Measured rib patch must remain one valid solid')
    return rib


def _annular_grooves(radius):
    # Median radial sections from 36 meridians; outer stations close above the shaft.
    offsets=[-1.2,-.8,-.6,-.45,-.3,-.15,0.,.15,.3,.45,.6,.8,1.2]
    profiles=[
        (14.07774,[2.620352,2.538118,2.505358,2.461242,2.411954,2.375530,2.359972,2.387442,2.428010,2.477168,2.524329,2.568001,2.620352]),
        (18.11595,[2.620352,2.602739,2.568305,2.520525,2.466132,2.428781,2.408108,2.429159,2.466278,2.513795,2.557495,2.594198,2.620352]),
        (22.15130,[2.620352,2.601418,2.563787,2.512046,2.456330,2.415426,2.405548,2.426151,2.464357,2.506788,2.541260,2.563355,2.620352]),
    ]
    for center,rs in profiles:
        stations=[(center+z,r*radius/2.590352) for z,r in zip(offsets,rs)]
        secants=[(r1-r0)/(z1-z0) for (z0,r0),(z1,r1) in zip(stations,stations[1:])]
        slopes=[0.]
        for i in range(1,len(stations)-1):
            h0=stations[i][0]-stations[i-1][0];h1=stations[i+1][0]-stations[i][0]
            a,b=secants[i-1],secants[i]
            slopes.append(0. if a*b<=0 else 3*(h0+h1)/((2*h1+h0)/a+(h1+2*h0)/b))
        slopes.append(0.)
        curves=[]
        for i,((z0,r0),(z1,r1)) in enumerate(zip(stations,stations[1:])):
            h=(z1-z0)/3
            curves.append(Edge.make_bezier((r0,0,z0),(r0+h*slopes[i],0,z0+h),(r1-h*slopes[i+1],0,z1-h),(r1,0,z1)))
        z0,r0=stations[0];z1,r1=stations[-1];outer=radius+.5
        wire=Wire([*curves,Edge.make_line((r1,0,z1),(outer,0,z1)),Edge.make_line((outer,0,z1),(outer,0,z0)),Edge.make_line((outer,0,z0),(r0,0,z0))])
        yield revolve(Face(wire),axis=Axis.Z)


@part
def palm_pilot_stylus(stylus_length=107.368,shaft_diameter=5.180704,tip_length=15.0,draft=False):
    """Scan-derived stylus with three shaft rings and five transverse grip grooves.

    stylus_length: observed tip-to-head length.
    shaft_diameter: fitted diameter of the circular shaft.
    tip_length: measured taper extent through its smooth join to the shaft.
    """
    radius=shaft_diameter/2
    tip=_round_tip(radius,tip_length)
    crown_top=stylus_length-.020
    head_start=stylus_length-1.368
    shaft=Pos(0,0,tip_length)*Cylinder(radius,head_start-tip_length,align=(Align.CENTER,Align.CENTER,Align.MIN))
    crown=Pos(0,0,crown_top-4.8)*Sphere(4.8)
    crown=crown & Pos(0,0,head_start)*Cylinder(radius,2,align=(Align.CENTER,Align.CENTER,Align.MIN))
    # The top is truncated by a tenth of a micron to avoid singular STL pole triangles.
    crown=crown & Pos(0,0,head_start)*Box(10,10,crown_top-head_start-.0001,align=(Align.CENTER,Align.CENTER,Align.MIN))
    result=tip.fuse(shaft,crown,_grip_rib(stylus_length))
    for groove in _annular_grooves(radius):
        result=result-groove
    # Use the measured negative-Y half: the two source sides average to this root profile.
    # An explicit mirror avoids asymmetry introduced by loft parameterization.
    half=result & Pos(0,-5,stylus_length/2)*Box(20,10,stylus_length+2)
    result=half.fuse(mirror(half,about=Plane.XZ))
    if not result.is_valid or len(result.solids())!=1:
        raise ValueError('Stylus must be one valid native solid')
    return result
