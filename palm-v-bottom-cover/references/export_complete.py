"""Export and reopen the whole-device reconstruction with per-component provenance."""
from pathlib import Path
import hashlib,json,time
import numpy as np,trimesh
from build123d import export_step,import_step
from nurb.builder import build,_triangulate
from OCP.BRepTools import BRepTools
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.BRepLib import BRepLib_ToolTriangulatedShape
from OCP.TopLoc import TopLoc_Location
from OCP.TopAbs import TopAbs_REVERSED
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def cad_normals(shape):
    values=[]
    for face in shape.faces():
        loc=TopLoc_Location()
        poly=BRep_Tool.Triangulation_s(face.wrapped,loc)
        if poly is None:continue
        BRepLib_ToolTriangulatedShape.ComputeNormals_s(face.wrapped,poly)
        sign=-1 if face.wrapped.Orientation()==TopAbs_REVERSED else 1
        for i in range(1,poly.NbNodes()+1):
            normal=poly.Normal(i).Transformed(loc.Transformation())
            values.append((sign*normal.X(),sign*normal.Y(),sign*normal.Z()))
    return np.asarray(values)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    started=time.time()
    shape=build(ROOT/'parts/palm_v_complete.py')[0]
    components=shape._nurb_scene.components
    print('Built',len(components),'components',round(time.time()-started,1),flush=True)
    step=OUT/'palm_v_complete.step';export_step(shape,step)
    reopened=import_step(step)
    if not reopened.is_valid or len(reopened.solids())!=len(components):raise ValueError('STEP reopen failed')
    print('STEP reopened',len(reopened.solids()),flush=True)
    scene=trimesh.Scene();closed=[];reports=[]
    for c in components:
        before=time.time()
        BRepTools.Clean_s(c.solid.wrapped)
        angle=.08 if c.label=='Smooth paired stylus channels' else .18
        mesher=BRepMesh_IncrementalMesh(c.solid.wrapped,.025,False,angle,True)
        if not mesher.IsDone():raise ValueError(f'Meshing failed for {c.label}')
        vertices,faces,_=_triangulate(c.solid,.09,remesh=False)
        points=np.asarray(vertices,dtype=np.float32).astype(np.float64).reshape(-1,3)
        triangles=np.asarray(faces).reshape(-1,3)
        cross=np.cross(points[triangles[:,1]]-points[triangles[:,0]],points[triangles[:,2]]-points[triangles[:,0]])
        keep=np.any(cross!=0,axis=1)
        dropped=int(np.count_nonzero(~keep))
        mesh=trimesh.Trimesh(points,triangles[keep],process=False)
        mesh.vertex_normals=cad_normals(c.solid)
        mesh.visual.vertex_colors=np.tile(np.round(np.array(tuple(c.solid.color))*255).astype('u1'),(len(mesh.vertices),1))
        scene.add_geometry(mesh,node_name=c.label,geom_name=c.label,metadata={'component':c.label})
        unique,inverse=np.unique(mesh.vertices,axis=0,return_inverse=True)
        welded=trimesh.Trimesh(unique,inverse[mesh.faces],process=False)
        reports.append({'name':c.label,'valid_brep':c.solid.is_valid,'solids':len(c.solid.solids()),'triangles':len(mesh.faces),'angular_deflection_rad':angle,'float32_zero_area_triangles_removed':dropped,'welded_watertight':welded.is_watertight,'winding_consistent':welded.is_winding_consistent,'volume_mm3':float(c.solid.volume)})
        closed.append(welded)
        print(c.label,reports[-1]['triangles'],reports[-1]['welded_watertight'],round(time.time()-before,1),flush=True)
    glb=OUT/'palm_v_complete.glb';glb.write_bytes(scene.export(file_type='glb'))
    reopened_glb=trimesh.load(glb)
    if len(reopened_glb.geometry)!=len(components):raise ValueError('GLB component names lost')
    combined=trimesh.util.concatenate(closed)
    stl=OUT/'palm_v_complete.stl';combined.export(stl)
    reopened_stl=trimesh.load(stl,process=True)
    inputs=[ROOT/'palm_front_geometry.py',ROOT/'palm_complete_geometry.py',*sorted((ROOT/'parts').glob('palm_v*.py')),*sorted((ROOT/'references').glob('*fit.json')),ROOT/'references/palm-assembly-poses.json',ROOT/'references/export_complete.py']
    report={'components':reports,'step_valid':reopened.is_valid,'step_solids':len(reopened.solids()),'glb_components':len(reopened_glb.geometry),'stl_watertight':reopened_stl.is_watertight,'stl_winding_consistent':reopened_stl.is_winding_consistent,'stl_bounds_mm':reopened_stl.bounds.tolist(),'artifact_sha256':{p.name:digest(p) for p in [step,glb,stl]},'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in inputs},'tessellation':{'linear_deflection_mm':.025,'relative':False,'angular_deflection_rad':.18,'frame_angular_deflection_rad':.08,'normals':'Native surface UV derivatives, transformed and face-oriented'},'limits':'Exterior component assembly. Separate coincident or overlapping component solids remain separate in STL; no claim of a fused print-ready object or manufactured internal fit. Colors identify materials, not scanner color data. Exact bilateral main forms preserve intentional asymmetric power, contrast and reset controls.','elapsed_seconds':time.time()-started}
    (OUT/'palm_v_complete-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','components']},indent=2),flush=True)
if __name__=='__main__':main()
