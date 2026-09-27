"""Guaranteed scan vertex -> closest triangle distance for original and two trials."""
import gzip,sys,json,time
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from build123d import import_step
from trimesh.triangles import closest_point
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'references'))
from import_observed_mesh import VDTYPE
with gzip.open(root/'scans/palm-v-bottom-cover-comparison-triangles.ply.gz','rb') as f:
 while f.readline()!=b'end_header\n':pass
 v=np.frombuffer(f.read(376165*VDTYPE.itemsize),VDTYPE)
paths={
 'baseline':root/'build/analysis/far-end-trials/baseline.step',
 'v4':root/'build/analysis/far-end-trials/v4.step',
 'v5b':root/'build/analysis/far-end-trials/v5b.step',
 'v5c':root/'build/analysis/far-end-trials/final-v5c.step',
}

class ExactTriangleIndex:
 def __init__(self,path):
  b=import_step(path);vertices,faces=b.tessellate(.04,.1)
  verts=np.array([tuple(q) for q in vertices]);self.tri=verts[np.asarray(faces)]
  self.centers=self.tri.mean(axis=1)
  self.radii=np.linalg.norm(self.tri-self.centers[:,None,:],axis=2).max(axis=1)
  self.vtree=cKDTree(verts)
  self.buckets=[]
  for lo,hi in zip([0,.25,.5,1,2,4,8,16,32],[.25,.5,1,2,4,8,16,32,64]):
   ids=np.flatnonzero((self.radii>lo)&(self.radii<=hi))
   if len(ids):self.buckets.append((ids,cKDTree(self.centers[ids]),hi))
 def distance(self,p):
  upper=float(self.vtree.query(p)[0])
  hit=0
  for ids,tree,hi in self.buckets:
   local=tree.query_ball_point(p,upper+hi)
   if not local:continue
   candidates=ids[local]
   # Any triangle closer than the current upper bound must have centroid within
   # upper+its true covering radius; the bucket search is a conservative superset.
   keep=np.linalg.norm(self.centers[candidates]-p,axis=1)<=upper+self.radii[candidates]
   candidates=candidates[keep]
   if not len(candidates):continue
   pts=np.repeat(p[None,:],len(candidates),axis=0)
   closest=closest_point(self.tri[candidates],pts)
   upper=min(upper,float(np.linalg.norm(closest-pts,axis=1).min()))
   hit+=len(candidates)
  return upper,hit
 def distances(self,points):
  out=np.zeros(len(points));hits=np.zeros(len(points),int)
  for i,p in enumerate(points):out[i],hits[i]=self.distance(p)
  return out,hits

x,y,z,ny,nz,g=[v[k] for k in ('x','y','z','ny','nz','source_group')]
common=(abs(x)>5)&(abs(x)<28)&(y>52)&(y<56.2)&(z>-.5)&(z<3.5)
masks={
 'g1_outer_skin':common&(g==1)&(nz<-.4),
 'g1_outer_root':common&(g==1)&(nz<-.4)&(y>54.4)&(y<55.6)&(z<1),
 'g2_inner_wall':common&(g==2)&(ny<-.65)&(z>.7),
 'g3_inner_wall':common&(g==3)&(ny<-.65)&(z>.7),
 'g2_inner_root':common&(g==2)&(y>54.2)&(y<55.5)&(z>.5)&(z<1.3),
 'g3_inner_root':common&(g==3)&(y>54.2)&(y<55.5)&(z>.5)&(z<1.3),
 'corner_g1_skin':(abs(x)>32)&(abs(x)<38)&(y>52)&(y<56)&(z>-.5)&(z<1.5)&(g==1)&(nz<-.4),
 'corner_g2_return':(abs(x)>32)&(abs(x)<38)&(y>52)&(y<56)&(z>.2)&(z<3.5)&(g==2),
 'corner_g3_return':(abs(x)>32)&(abs(x)<38)&(y>52)&(y<56)&(z>.2)&(z<3.5)&(g==3),
}
points={}
for name,mask in masks.items():
 p=np.column_stack([x[mask],y[mask],z[mask]])
 if len(p)>1100:p=p[np.random.default_rng(17).choice(len(p),1100,replace=False)]
 points[name]=p
print('points',[(k,len(p)) for k,p in points.items()],flush=True)
result={}
for name,path in paths.items():
 start=time.monotonic();idx=ExactTriangleIndex(path)
 print('INDEX',name,len(idx.tri),'time',time.monotonic()-start,flush=True)
 result[name]={}
 for region,p in points.items():
  a,hits=idx.distances(p)
  result[name][region]={'n':len(a),'median':float(np.median(a)),'p90':float(np.quantile(a,.9)),'p95':float(np.quantile(a,.95)),'max':float(a.max()),'mean_triangle_candidates':float(hits.mean())}
  print(name,region,result[name][region],flush=True)
 print('DONE',name,'time',time.monotonic()-start,flush=True)
(root/'build/analysis/far-end-trials/robust-fit.json').write_text(json.dumps(result,indent=2))
