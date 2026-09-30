"""Save the named Pilot assembly and a watertight combined mesh.

Run with Python from the environment that contains nurb. Normal `nurb export`
already writes the fixed body, battery cover, memory cover and stylus downloads.
"""
from copy import copy
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from build123d import Compound, export_step, import_step
from nurb import builder
import numpy as np
import trimesh


def require_closed_mesh(mesh):
    """Validate exact-coordinate topology without welding nearby points or repair."""
    points = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=int)
    if not len(faces) or not np.isfinite(points).all():
        raise ValueError('Export mesh must contain finite triangle geometry')
    points, inverse = np.unique(points, axis=0, return_inverse=True)
    faces = inverse[faces]
    triangles = points[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    if np.any(~np.any(cross != 0, axis=1)):
        raise ValueError('Export mesh contains a zero-area triangle')
    if len(np.unique(np.sort(faces, axis=1), axis=0)) != len(faces):
        raise ValueError('Export mesh contains duplicate triangles')
    indexed = trimesh.Trimesh(vertices=points, faces=faces, process=False)
    if not indexed.is_watertight or not indexed.is_winding_consistent:
        raise ValueError('Export mesh must have closed boundaries and consistent winding')
    for shell in indexed.split(only_watertight=False):
        if shell.volume == 0:
            raise ValueError('Export mesh contains a zero-volume boundary shell')
    return indexed


def precise_stl(mesh,path):
    """Keep tiny valid facets intact after the assembly moves them far from origin."""
    points=np.asarray(mesh.vertices,dtype=float)
    faces=np.asarray(mesh.faces,dtype=int)
    require_closed_mesh(mesh)
    with TemporaryDirectory(prefix='.palm-export-', dir=path.parent) as scratch:
        pending = Path(scratch) / path.name
        with pending.open('w') as out:
            out.write('solid PalmPilot\n')
            for face in faces:
                t=points[face];n=np.cross(t[1]-t[0],t[2]-t[0]);n/=np.linalg.norm(n)
                out.write('facet normal '+' '.join(format(v,'.17g') for v in n)+'\nouter loop\n')
                for p in t:out.write('vertex '+' '.join(format(v,'.17g') for v in p)+'\n')
                out.write('endloop\nendfacet\n')
            out.write('endsolid PalmPilot\n')
        require_closed_mesh(trimesh.load(pending, process=False))
        pending.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',choices=['closed','covers_open','covers_removed','withdrawn'],default='closed')
    args=parser.parse_args()
    poses={'closed':{},'covers_open':{'battery_slide':25.0,'memory_slide':22.0},'covers_removed':{'battery_slide':60.0,'memory_slide':60.0},'withdrawn':{'stylus_withdrawal':30.0}}
    overrides=poses[args.variant]
    suffix='' if args.variant=='closed' else '-'+args.variant
    root = Path(__file__).resolve().parent
    build = root / 'build'
    build.mkdir(exist_ok=True)
    shape, _, milliseconds = builder.build(root / 'parts/palm_pilot_professional.py',overrides=overrides)
    components = [c for c in shape._nurb_scene.components if not c.group]
    named = []
    for component in components:
        item = copy(component.solid)
        item.label = component.label
        named.append(item)
    assembly = Compound(children=named)
    step_path = build / f'palm_pilot_professional{suffix}.step'
    export_step(assembly, step_path)
    reopened = import_step(step_path)
    if len(reopened.solids()) != len(components) or not reopened.is_valid:
        raise RuntimeError('Saved STEP must preserve every valid named component')
    body_pieces=[copy(c.solid) for c in components if c.label!='Stylus']
    body=body_pieces[0].fuse(*body_pieces[1:])
    verification=build/'cover-verification'
    verification.mkdir(exist_ok=True)
    body_mesh_path=verification/f'assembled-body{suffix}.stl'
    builder.write_stl(body,body_mesh_path)
    stylus = next(c.solid for c in components if c.label == 'Stylus')
    placement=stylus.location
    local_stylus=placement.inverse()*copy(stylus)
    local_stylus_path=verification/f'assembly-stylus-local{suffix}.stl'
    builder.write_stl(local_stylus,local_stylus_path)
    transform=np.eye(4)
    native_transform=placement.wrapped.Transformation()
    for row in range(3):
        for column in range(4):
            transform[row,column]=native_transform.Value(row+1,column+1)
    body_mesh=trimesh.load(body_mesh_path,process=True)
    stylus_mesh=trimesh.load(local_stylus_path,process=True)
    stylus_mesh.apply_transform(transform)
    combined_mesh=trimesh.util.concatenate([body_mesh,stylus_mesh])
    stl_path = build / f'palm_pilot_professional{suffix}.stl'
    precise_stl(combined_mesh, stl_path)
    constituents=[]
    for path,matrix in [(body_mesh_path,np.eye(4)),(local_stylus_path,transform)]:
        constituents.append({'path':str(path.relative_to(root)),
                             'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                             'transform':matrix.tolist()})
    mesh = trimesh.load(stl_path, process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise RuntimeError('Saved assembly STL must be watertight with consistent winding')
    glb_path = build / f'palm_pilot_professional{suffix}.glb'
    glb_path.write_bytes(builder.to_glb(shape, .02))
    inventory = [
        {'label': c.label, 'solids': len(c.solid.solids()), 'valid': c.solid.is_valid, 'volume_mm3': c.solid.volume}
        for c in components
    ]
    files = {}
    for path in [step_path, stl_path, glb_path]:
        files[path.name] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    report = {
        'variant':args.variant,
        'pose_parameters':overrides,
        'build_ms': milliseconds,
        'native_component_count': len(components),
        'reopened_step_solids': len(reopened.solids()),
        'stl_triangles': len(mesh.faces),
        'stl_closed_components': len(mesh.split(only_watertight=False)),
        'stl_watertight': bool(mesh.is_watertight),
        'stl_encoding':'ASCII with 17 significant digits; no positive-area facets deleted or repaired',
        'mesh_constituents':constituents,
        'components': inventory,
        'artifacts': files,
        'mesh_representation': 'Validated body-union and local stylus meshes are combined after double-precision placement. CAD union removes internal coincident body contacts; STEP preserves named components.',
    }
    destination = build / 'cover-verification'
    destination.mkdir(exist_ok=True)
    (destination / f'assembly-export{suffix}.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['reopened_step_solids', 'stl_triangles', 'stl_closed_components', 'stl_watertight']}, indent=2))
    for path in [step_path, stl_path, glb_path]:
        print(path)


if __name__ == '__main__':
    main()
