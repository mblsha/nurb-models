"""Fit a low-control, exactly mirrored exterior frame to the assembled scan."""
from pathlib import Path
import gzip,hashlib,io,json,numpy as np,trimesh
ROOT=Path(__file__).resolve().parents[1]
scan=trimesh.load(io.BytesIO(gzip.decompress((ROOT/'scans/palm-v-rough-observed.ply.gz').read_bytes())),file_type='ply',process=False)
frame=json.loads((ROOT/'references/palm-new-reference-frames.json').read_text())['whole']['source_to_canonical']
scan.apply_transform(np.array(frame))
levels=[-4.25,-4.0,-3.75,-3.5,-3.25,-3.0,-2.5,-1.5,-.5,0,.5,.8,1.0,1.2,1.4,1.65]
rows=[]
for z in levels:
 seg=trimesh.intersections.mesh_plane(scan,plane_origin=(0,0,z),plane_normal=(0,0,1))
 def crossing(axis,v,positive):
  a=seg[:,0,axis];b=seg[:,1,axis];m=(a-v)*(b-v)<=0
  aa=seg[m,0];bb=seg[m,1];t=(v-aa[:,axis])/(bb[:,axis]-aa[:,axis]+1e-20)
  vals=(aa+t[:,None]*(bb-aa))[:,1-axis]
  vals=vals[vals>0] if positive else vals[vals<0]
  return (max(vals) if positive else min(vals))
 def side(y):
  return .5*(crossing(1,y,True)-crossing(1,y,False))
 def end(x,top):
  return .5*(crossing(0,x,top)+crossing(0,-x,top))
 main=float(np.median([side(y) for y in [-30,-15,0,15,30,40]]))
 p=[]
 for x in [0,10,20,28,32]:p.append([x,end(x,True)])
 for y in [55,53,50,40,20,0,-20,-30,-35,-40,-44,-47,-49]:
  p.append([main if -30<=y<=40 else side(y),y])
 # At the widest lower flare the bottom rolls inward rapidly.
 for x in [36,32,26,20,10,0]:p.append([x,end(x,False)])
 rows.append({'z_mm':z,'half_outline_xy_mm':p,'main_halfwidth_mm':main})
data={'source':'scans/palm-v-rough-observed.ply.gz','source_sha256':hashlib.sha256((ROOT/'scans/palm-v-rough-observed.ply.gz').read_bytes()).hexdigest(),'method':'Exact sections of the original whole-device triangles in the saved canonical datum; left/right crossing average; straight long rails replace scan ripple; cubic half contours mirror exactly. Exterior only, hidden core is unspecified.','levels':rows}
(ROOT/'references/complete-frame-fit.json').write_text(json.dumps(data,indent=2)+'\n')
print([(r['z_mm'],round(r['main_halfwidth_mm'],3)) for r in rows],flush=True)
