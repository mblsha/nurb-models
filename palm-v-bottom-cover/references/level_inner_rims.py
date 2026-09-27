import sys
import json
import hashlib
from pathlib import Path
import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import brentq
from scipy.sparse import csr_matrix, vstack, eye
from scipy.sparse.linalg import lsmr
from OCP.BRep import BRep_Tool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'parts'))
from palm_v_bottom_cover import exterior_surface

surf = BRep_Tool.Surface_s(exterior_surface(level_inner_rims=False).wrapped)
for knot in (-32.5,-30.0,-27.5,-25.0,-22.5,-20.0,-17.5,-15.0,-12.5):
 surf.InsertVKnot(knot,1,1e-9)
nu,nv=surf.NbUPoles(),surf.NbVPoles()
K1=np.repeat([surf.UKnot(i+1) for i in range(surf.NbUKnots())],[surf.UMultiplicity(i+1) for i in range(surf.NbUKnots())])
K2=np.repeat([surf.VKnot(i+1) for i in range(surf.NbVKnots())],[surf.VMultiplicity(i+1) for i in range(surf.NbVKnots())])
Bu=BSpline(K1,np.eye(nu),3); Bv=BSpline(K2,np.eye(nv),3)
Du=Bu.derivative(); Dv=Bv.derivative()
coords=np.array([[[*surf.Pole(i+1,j+1).Coord()] for j in range(nv)] for i in range(nu)])
bands={b['name']:b for b in json.loads((ROOT / 'references/straight-rim-fit.json').read_text())['targets']}
side=np.array([[brentq(lambda u:surf.Value(u,v).Z()-1.30,35,41),v] for v in np.linspace(-35,40,100)])
far=np.array([[u,58.7] for u in np.linspace(0,28,40)])
near_b=bands['split_end']; a=np.array(near_b['uv_a']); b=np.array(near_b['uv_b']); near=np.array([a+t*(b-a) for t in np.linspace(0,1,30)])
UV=np.vstack([side,far,near]); labels=np.r_[np.zeros(len(side)),np.ones(len(far)),np.ones(len(near))*2]
def matrix(b1,b2): return np.einsum('ki,kj->kij',b1,b2).reshape(len(UV),-1)
Bm=matrix(Bu(UV[:,0]),Bv(UV[:,1])); Um=matrix(Du(UV[:,0]),Bv(UV[:,1])); Vm=matrix(Bu(UV[:,0]),Dv(UV[:,1]))
# Tie mirrored Z poles together, including the center column only once.
mirrors=[]
for i in range(nu//2,nu):
 for j in range(nv):
  k=i*nv+j; q=(nu-1-i)*nv+j
  if np.max(np.abs(Um[:,k]) + np.abs(Vm[:,k]) + np.abs(Bm[:,k])) < 1e-7:continue
  mirrors.append((k,q))
def pair(mat):return np.column_stack([mat[:,k]+(mat[:,q] if q!=k else 0) for k,q in mirrors])
B=pair(Bm); U=pair(Um); V=pair(Vm)
active=np.flatnonzero(np.max(np.abs(U)+np.abs(V),axis=0)>1e-6)
B=B[:,active];U=U[:,active];V=V[:,active]; links=[mirrors[i] for i in active]
print('variables',len(links),flush=True)
z0=Bm@coords[:,:,2].ravel(); x=coords[:,:,0].ravel();y=coords[:,:,1].ravel();zu0=Um@coords[:,:,2].ravel();zv0=Vm@coords[:,:,2].ravel();xu=Um@x;xv=Vm@x;yu=Um@y;yv=Vm@y
def normals(du,dv):
 cx=yu*dv-du*yv;cy=du*xv-xu*dv;cz=xu*yv-yu*xv;c2=cx*cx+cy*cy+cz*cz;c=np.sqrt(c2)
 n=cz/c
 dn_du=-cz*(cx*(-yv)+cy*xv)/(c2*c)
 dn_dv=-cz*(cx*yu+cy*(-xu))/(c2*c)
 return n,dn_du,dn_dv
target=np.array([0.128,0.073,0.135])[labels.astype(int)]
delta=np.zeros(len(links))
for it in range(6):
 n,du,dv=normals(zu0+U@delta,zv0+V@delta)
 J=du[:,None]*U+dv[:,None]*V
 rhs=target-n
 # Constrain the exterior edge to exactly its current elevation; target the
 # offset-surface normals only in its narrow supporting bend band.
 A=vstack([csr_matrix(J)*20,csr_matrix(B)*1000,eye(len(links))*0.8]).tocsr()
 step=lsmr(A,np.r_[rhs*20,-(B@delta)*1000,-delta*0.8],atol=1e-12,btol=1e-12,maxiter=5000)[0]
 delta+=step
 print('iteration',it,'norm p2p',[np.ptp(n[labels==k]) for k in (0,1,2)],'edge max',max(abs(B@delta)),'stepmax',max(abs(step)),flush=True)
print('delta max',max(abs(delta)),'z bound',max(abs(B@delta)))
for k in (0,1,2):
 n=normals(zu0+U@delta,zv0+V@delta)[0][labels==k]
 print('end',k,'normal z span',np.ptp(n),'approx inner span',.65*np.ptp(n))
 if k == 0:
  for v, q in zip(side[:,1][::5], n[::5]): print('  side',round(v,1),round(q,5))
corrections=[]
for amount,(k,q) in zip(delta,links):
 if abs(amount)<1e-8:continue
 i,j=divmod(k,nv);corrections.append([int(i),int(j),float(amount)])
result = {
 'straight_rim_fit_sha256':hashlib.sha256((ROOT/'references/straight-rim-fit.json').read_bytes()).hexdigest(),
 'extra_v_knots':[-32.5,-30.0,-27.5,-25.0,-22.5,-20.0,-17.5,-15.0,-12.5],
 'pole_grid':[nu,nv],
 'symmetric_z_pole_corrections':corrections,
 'objective':'level normal-offset inner core crests with original exterior boundary fixed; side Y -35..40, +Y X 0..28, -Y X 18..36',
}
(ROOT/'references/inner-rim-fit.json').write_text(json.dumps(result,indent=2)+'\n')
