"""Finite sampled exterior audit in the saved whole-PDA datum, with exact mesh distances.

Uses nurb.compare's dependency-free point/triangle distance kernel. Exact triangle-ray
visibility from 26 exterior directions removes hidden assembly faces from CAD samples.
A surface visible only through a narrower direction may be omitted; visibility is a
sampling scope, not a topological proof. Source samples whose nearest CAD match is
buried are reported explicitly and not represented as successful exterior matches.
"""
import argparse,json,subprocess,tempfile,hashlib,gzip,io,shutil
from pathlib import Path
import numpy as np,trimesh
from nurb import compare
from read_palm_reference import whole_reference

ROOT=Path(__file__).resolve().parents[1]

def visibility_program():
 source=Path(__file__).with_name("complete_visibility_bvh.cpp")
 digest=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
 binary=Path(tempfile.gettempdir())/("palm-complete-visibility-"+digest)
 if not binary.exists():
  compiler=shutil.which("clang++") or shutil.which("c++")
  if not compiler:raise RuntimeError("A C++17 compiler is required for exact visibility validation")
  subprocess.run([compiler,"-O3","-std=c++17",str(source),"-o",str(binary)],check=True)
 return binary

def load_components(path):
 obj=trimesh.load(path,process=False)
 if isinstance(obj,trimesh.Trimesh):return obj,[{'name':path.stem,'faces':len(obj.faces)}]
 meshes=[];meta=[]
 for node in obj.graph.nodes_geometry:
  transform,key=obj.graph[node];mesh=obj.geometry[key].copy();mesh.apply_transform(transform)
  meshes.append(mesh);meta.append({'name':node,'geometry':key,'faces':len(mesh.faces),'bounds':mesh.bounds.tolist()})
 return trimesh.util.concatenate(meshes),meta

def visible(points,surface):
 triangles,_=surface
 with tempfile.TemporaryDirectory(prefix='palm-rays-') as folder:
  root=Path(folder)
  with (root/'mesh.bin').open('wb') as f:
   np.asarray([len(triangles)],dtype=np.uint64).tofile(f);np.asarray(triangles,dtype=np.float64).tofile(f)
  with (root/'points.bin').open('wb') as f:
   np.asarray([len(points)],dtype=np.uint64).tofile(f);np.asarray(points,dtype=np.float64).tofile(f)
  subprocess.run([str(visibility_program()),str(root/'mesh.bin'),str(root/'points.bin'),str(root/'out.bin')],check=True)
  return np.fromfile(root/'out.bin',dtype=np.uint8).astype(bool)

def masks(p):
 x,y,z=p.T;keys=np.zeros(len(p),bool)
 for cx,cy in [(-26.2,-42),(-13,-44),(13,-44),(26.2,-42)]:keys|=((x-cx)**2+(y-cy)**2<4.5**2)&(z>2)
 rocker=(abs(x)<4.5)&(y>-55)&(y<-38)&(z>2)
 display=(abs(x)<28.6)&(y>-31)&(y<46)&(z>2)
 return {'global':np.ones(len(p),bool),'front_skin':(z>1)&~keys&~rocker&~display,'display':display,'application_keys':keys,'scroll_rocker':rocker,'rear_skin':(z<-4)&(y>-44)&(abs(x)<35),'side_channels':(abs(x)>34)&(abs(y)<45)&(z>-4)&(z<2),'dock':(abs(x)<17)&(y<-45)&(z<0),'top_controls':(y>50)&(abs(x)>17)&(z>0)}

def stats(d,tol):
 if not len(d):return {'samples':0}
 return {'samples':len(d),'median_mm':float(np.median(d)),'p95_mm':float(np.quantile(d,.95)),'p99_mm':float(np.quantile(d,.99)),'sampled_max_mm':float(max(d)),'within_tolerance_fraction':float(np.mean(d<=tol))}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('model',type=Path,nargs='?',default=ROOT/'build/palm_v_complete.glb')
 ap.add_argument('--reference',type=Path,help='Optional already aligned reference mesh; default preserves original PLY and frozen whole datum')
 ap.add_argument('--output',type=Path,default=ROOT/'build/palm_v_complete-comparison.json')
 ap.add_argument('--self-test',action='store_true',help='Check that nested-box inner surfaces are rejected')
 ap.add_argument('--samples',type=int,default=3500)
 ap.add_argument('--tolerance',type=float,default=.5)
 a=ap.parse_args()
 if a.self_test:
  compare.MAX_EDGE=1.0
  outer=trimesh.creation.box([8,8,8]);inner=trimesh.creation.box([4,4,4])
  surface=compare._surface(trimesh.util.concatenate([outer,inner]))
  outside,_=trimesh.sample.sample_surface(outer,150,seed=1)
  inside,_=trimesh.sample.sample_surface(inner,150,seed=1)
  result=visible(np.vstack([outside,inside]),surface)
  if not result[:150].all() or result[150:].any():raise AssertionError('Visibility self-test failed')
  print('Passed: all 150 exterior samples retained; all 150 buried samples rejected')
  return
 if not a.model.is_absolute():a.model=ROOT/a.model
 if not a.output.is_absolute():a.output=ROOT/a.output
 if a.reference is None:
  reference_path=ROOT/'scans/palm-v-rough-observed.ply.gz'
  loaded=trimesh.load(io.BytesIO(gzip.decompress(reference_path.read_bytes())),file_type='ply',process=False)
  points,normals,frame=whole_reference()
  transform=np.array(frame['source_to_canonical'])
  if not np.allclose(loaded.vertices@transform[:3,:3].T+transform[:3,3],points,atol=1e-9):raise ValueError('PLY triangle indices do not match preserved reference reader')
  ref=trimesh.Trimesh(points,loaded.faces,process=False)
 else:
  reference_path=a.reference if a.reference.is_absolute() else ROOT/a.reference
  ref=trimesh.load(reference_path,force='mesh',process=False)
  frame={'source_to_canonical':np.eye(4).tolist(),'status':'Already aligned explicit reference'}
 def label(path):
  try:return str(path.relative_to(ROOT))
  except ValueError:return str(path)
 compare.MAX_EDGE=1.0
 model_hash=hashlib.sha256(a.model.read_bytes()).hexdigest()
 model,components=load_components(a.model)
 print('Preparing model/reference distance surfaces',flush=True);ms=compare._surface(model);rs=compare._surface(ref)
 cp,cf=trimesh.sample.sample_surface(model,a.samples*2,seed=42);rp,rf=trimesh.sample.sample_surface(ref,a.samples,seed=43)
 print('Filtering CAD samples to exposed faces',flush=True);cv=visible(cp,ms);cp=cp[cv]
 print('Exact CAD-to-scan distances',flush=True);cd=compare._to_surface(cp,rs)
 print('Exact scan-to-CAD distances',flush=True);rd,matched=compare._to_surface(rp,ms,closest=True)
 print('Checking nearest CAD matches are exposed',flush=True);rv=visible(matched,ms)
 report={'model_sha256':model_hash,'reference_sha256':hashlib.sha256(reference_path.read_bytes()).hexdigest(),'reference_frame':frame,'validator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'visibility_source_sha256':hashlib.sha256(Path(__file__).with_name('complete_visibility_bvh.cpp').read_bytes()).hexdigest(),'model':label(a.model),'reference':label(reference_path),'components':components,'units':'mm','tolerance_mm':a.tolerance,'model_bounds':model.bounds.tolist(),'reference_bounds':ref.bounds.tolist(),'method':'Exact unsigned point-to-triangle distances using nurb.compare. Area-uniform random samples; CAD exposure checked by unobstructed exact triangle rays in 26 directions. Buried CAD samples excluded. Any source sample with a buried nearest CAD match remains explicitly unresolved, not a successful exterior match. Limited directions can exclude exposed points seen only through a narrower aperture. Mesh metrics include tessellation error and are finite samples, not certified maxima.','cad_area_samples_total':len(cv),'cad_exposed_samples':int(cv.sum()),'source_samples':len(rv),'source_nearest_cad_match_buried':int((~rv).sum()),'regions':{}}
 cm=masks(cp);rm=masks(rp)
 for region in cm:
  report['regions'][region]={'cad_to_scan':stats(cd[cm[region]],a.tolerance),'scan_to_cad_all_nearest':stats(rd[rm[region]],a.tolerance),'scan_to_exposed_cad_confirmed':stats(rd[rm[region]&rv],a.tolerance),'unresolved_buried_matches':int((rm[region]&~rv).sum())}
 # Mask both sides of intentional asymmetric controls/reset landmarks.
 symmetric=~((abs(cp[:,0])>17)&(cp[:,1]>49)) & ~((abs(cp[:,0])<17)&(cp[:,1]>12)&(cp[:,1]<24)&(cp[:,2]<-3))
 mirror=cp[symmetric].copy();mirror[:,0]*=-1;sd=compare._to_surface(mirror,ms);report['symmetry']=stats(sd,.05);report['symmetry']['scope']='Exposed sample reflections about saved X=0 datum, excluding both sides of top power/contrast region and rear reset/label region; nearest complete CAD triangle surface.'
 worst=np.argsort(cd)[-30:][::-1];report['worst_cad_to_scan']=[{'point':p.tolist(),'distance_mm':float(d)} for p,d in zip(cp[worst],cd[worst])]
 worst=np.argsort(rd)[-30:][::-1];report['worst_scan_to_cad']=[{'point':p.tolist(),'distance_mm':float(d),'nearest_exposed':bool(vis)} for p,d,vis in zip(rp[worst],rd[worst],rv[worst])]
 if hashlib.sha256(a.model.read_bytes()).hexdigest()!=model_hash:raise RuntimeError('Model artifact changed during validation; rerun on frozen export')
 a.output.write_text(json.dumps(report,indent=2)+'\n');np.savez(a.output.with_suffix('.npz'),cad_points=cp,cad_distances=cd,reference_points=rp,reference_distances=rd,reference_nearest_exposed=rv)
 print(json.dumps({'regions':report['regions'],'symmetry':report['symmetry']},indent=2))
if __name__=='__main__':main()
