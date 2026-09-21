from pathlib import Path
import json,sys
import numpy as np,trimesh
from scipy.spatial import cKDTree
OUT=Path(__file__).parent;D=json.loads((OUT/'vision-pro-narrow-reference-sections.json').read_text());P=json.loads((OUT/'vision-pro-narrow-profile-samples.json').read_text());from build123d import import_step, Compound
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
body=import_step(sys.argv[1] if len(sys.argv)>1 else OUT.parent/'build'/'vision_pro_light_seal_13w.step');results={}
def samples(paths,spacing=.04):
 out=[]
 for path in paths:
  p=np.array(path)
  for a,b in zip(p[:-1],p[1:]):
   count=max(1,int(np.ceil(np.linalg.norm(b-a)/spacing)));out.extend(a+(b-a)*np.arange(count)[:,None]/count)
 return np.array(out)
def widths(paths,depth):
 hits=[]
 for path in paths:
  p=np.array(path);a=p[:-1];b=p[1:];dd=b[:,1]-a[:,1];mask=(abs(dd)>1e-9)&((a[:,1]-depth)*(b[:,1]-depth)<=0);f=(depth-a[mask,1])/dd[mask];u=a[mask,0]+f*(b[mask,0]-a[mask,0]);hits.extend(u[(u>-10)&(u<16)].tolist())
 hits=sorted(hits);return hits[:2] if len(hits)>=2 else None
def stats(d):return {'count':len(d),'median_mm':float(np.median(d)),'p95_mm':float(np.quantile(d,.95)),'max_mm':float(d.max())} if len(d) else None
for key in ['0','5','8','11']:
 r=D[key]['right'];tip=P[key]['paired_tip_local_uv'];origin=np.array(r['origin']);normal=np.array(r['toward_vision_pro']);inw=np.array(r['inward']);tangent=np.array(r['tangent']);paths={}
 for side in ['right','left']:
  if D[key][side]:paths[side]=[np.column_stack([np.array(p['local'])[:,0],tip[1]-np.array(p['local'])[:,1]]).tolist() for p in D[key][side]['paths']]
 print('Computing B-rep section', key, flush=True)
 sec=BRepAlgoAPI_Section(body.wrapped,gp_Pln(gp_Pnt(*origin),gp_Dir(*tangent)),False);sec.Approximation(True);sec.Build()
 if not sec.IsDone():raise RuntimeError('CAD section failed at '+key)
 cad=[]
 for edge in Compound(sec.Shape()).edges():
  count=max(4,int(np.ceil(edge.length/.04))+1);q=np.array([tuple(edge.position_at(float(t))) for t in np.linspace(0,1,count)]);uv=np.column_stack([(q-origin)@inw,tip[1]-(q-origin)@normal]);
  if np.linalg.norm(uv,axis=1).min()<16:cad.append(uv.tolist())
 paths['cad']=cad;sp=np.vstack([samples(paths[side]) for side in ['right','left'] if side in paths]);cp=samples(cad);scan_tree=cKDTree(sp);cad_tree=cKDTree(cp);metrics={}
 for label,lo,hi in [('complete_small_lip',0,5.5),('neck',.2,2.2),('tiny_base_and_undercut',2.2,4.2),('wall_join',4.2,5.5)]:
  def mask(p):return (p[:,0]>-6)&(p[:,0]<8)&(p[:,1]>=lo)&(p[:,1]<=hi)
  ca=cp[mask(cp)];sa=sp[mask(sp)];metrics[label]={'depth_mm':[lo,hi],'cad_to_scan':stats(scan_tree.query(ca)[0]),'scan_to_cad':stats(cad_tree.query(sa)[0])}
 checks={}
 for dep in [1.6,3,4,6,12,15]:
  bounds=widths(cad,dep);checks[str(dep)]={'outer_u':bounds[0],'inner_u':bounds[1],'width':bounds[1]-bounds[0]} if bounds else None
 vals=[]
 for dep in np.arange(2.3,3.51,.05):
  bounds=widths(cad,dep)
  if bounds:vals.append((dep,bounds[0]))
 a=widths(cad,2);b=widths(cad,4)
 if a and b and vals:
  dd=np.array([q[0] for q in vals]);uu=np.array([q[1] for q in vals]);base=a[0]+(b[0]-a[0])*(dd-2)/2;ix=np.argmax(base-uu);checks['small_outer_projection_mm']=float((base-uu)[ix]);checks['projection_depth_mm']=float(dd[ix])
 results[key]={'station':int(key),'paths':paths,'metrics':metrics,'section_widths':checks};print(key,json.dumps({'metrics':metrics,'widths':checks}),flush=True)
metadata={'status':'superseded_visualization_only','acceptance_evidence':False,'pooled_scan_sides':True,'superseded_by':'interface-validation.json#/narrow_vision_pro_interface','warning':'Nearest distances pool right and left scan samples. Use the side-labelled canonical interface validation for acceptance.'}
(OUT/'vision-pro-narrow-lip-contours.json').write_text(json.dumps({**metadata,'stations':results}));(OUT/'vision-pro-narrow-lip-metrics.json').write_text(json.dumps({**metadata,'stations':{k:{'metrics':v['metrics'],'section_widths':v['section_widths']} for k,v in results.items()}},indent=2))
