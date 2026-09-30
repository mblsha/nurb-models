"""Build, measure and export the registered front/back/PCB assembly."""
from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
import trimesh
from build123d import Color, Compound, Pos, import_step, export_step
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepTools import BRepTools
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
from nurb.builder import build, _triangulate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from case_profiles import mounted_holes


class AlignmentError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AlignmentError(message)


def intersector(shape):
    tool = IntCurvesFace_ShapeIntersector()
    tool.Load(shape.wrapped, 1e-7)
    return tool


def intersections(tool, origin, direction, lo, hi):
    tool.Perform(gp_Lin(gp_Pnt(*origin), gp_Dir(*direction)), lo, hi)
    require(tool.IsDone(), 'CAD surface intersection failed')
    return sorted({round(tool.WParameter(i), 9) for i in range(1, tool.NbPnt() + 1)})


def measure_bores(shapes):
    """Find actual opposite bore-wall intersections, including NURBS cylinders."""
    rows = []
    levels = {'Front': (-7.3, -7.1), 'Back': (-9.8, -9.3), 'PCB': (-8.2, -7.8)}
    for name, shape in shapes.items():
        tool = intersector(shape)
        radius = 1.3 if name == 'PCB' else 1.2
        for hole, (x, y) in enumerate(mounted_holes(), 1):
            for z in levels[name]:
                require(not shape.is_inside((x, y, z)), f'{name} hole {hole} is obstructed')
                midpoints = []
                for direction in [(1, 0, 0), (0, 1, 0), (math.sqrt(.5), math.sqrt(.5), 0), (math.sqrt(.5), -math.sqrt(.5), 0)]:
                    hits = intersections(tool, (x, y, z), direction, -1.8, 1.8)
                    negative = [t for t in hits if t < -1e-5]
                    positive = [t for t in hits if t > 1e-5]
                    require(negative and positive, f'{name} hole {hole} is missing opposite bore walls')
                    lo, hi = max(negative), min(positive)
                    midpoints.append((lo + hi) / 2)
                    require(abs((hi - lo) / 2 - radius) < .001, f'{name} hole {hole} has the wrong bore section')
                measured = [x + midpoints[0], y + midpoints[1]]
                error = math.dist(measured, [x, y])
                require(error < .001 and max(map(abs, midpoints)) < .001, f'{name} hole {hole} is not coaxial with the common datum')
                rows.append({'part': name, 'hole': hole, 'z_mm': z, 'measured_xy_mm': measured, 'axis_error_mm': error, 'radius_mm': radius})
    return rows


def measure_seats(shapes):
    tools = {name: intersector(shape) for name, shape in shapes.items()}
    rows = []
    for hole, (x, y) in enumerate(mounted_holes(), 1):
        # The annulus at radius 1.8 mm belongs to all three screw seats, outside their bores.
        spans = {}
        for name, tool in tools.items():
            hits = intersections(tool, (x + 1.8, y, 0), (0, 0, 1), -25, 10)
            require(len(hits) >= 2, f'{name} mounting land {hole} is missing')
            spans[name] = [min(hits), max(hits)]
        front_gap = spans['Front'][0] - spans['PCB'][1]
        back_gap = spans['PCB'][0] - spans['Back'][1]
        require(abs(front_gap) < .001, f'PCB does not seat against front post {hole}')
        require(abs(back_gap - .1) < .001, f'PCB/back clearance changed at mounting land {hole}')
        rows.append({'hole': hole, 'front_to_pcb_mm': front_gap, 'pcb_to_back_mm': back_gap, 'part_z_spans_mm': spans})
    return rows


def measure_interference(shapes):
    rows = []
    for first, second in [('Front', 'Back'), ('Front', 'PCB'), ('Back', 'PCB')]:
        print(f'Checking {first} / {second}', flush=True)
        common = shapes[first] & shapes[second]
        volume = abs(common.volume) if common else 0.0
        require(volume < 1e-5, f'{first} intersects {second}: {volume:g} mm3')
        rows.append({'first': first, 'second': second, 'intersection_mm3': volume})
    return rows


def measure_shell_seam(shapes):
    from build123d import Vertex, Rot
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from case_profiles import rear_outline, back_height, REAR_X, REAR_Y, REAR_YAW
    pose = Pos(REAR_X, REAR_Y, 0) * Rot(0, 0, REAR_YAW)
    tool = BRepExtrema_DistShapeShape()
    tool.LoadS1(shapes['Front'].shells()[0].wrapped)
    groups = {'ordinary': [], 'shoulder_edge': [], 'catch_receiver': [], 'shoulder_underlap': []}
    def sample(x, y, group):
        point = pose * Vertex(x, y, back_height(x, y))
        tool.LoadS2(point.wrapped)
        tool.Perform()
        require(tool.IsDone(), 'Could not measure the shell seam')
        groups[group].append(tool.Value())
    for edge in rear_outline().edges():
        for t in np.linspace(0, 1, max(2, math.ceil(edge.length)), endpoint=False):
            p = edge.position_at(float(t))
            group = 'shoulder_edge' if p.X > 30 and p.Y > 30 else 'ordinary'
            catches = [-49, -19.8, 9, 29.4] if p.Y > 0 else [-50.5, -35.8, -12.7, 16, 52]
            if abs(p.Y) > 37 and any(abs(p.X - x) < 2.6 for x in catches):
                group = 'catch_receiver'
            sample(p.X, p.Y, group)
    for x, edge in [(35,39.8),(38,40.1),(40,40.65),(43,41.5),(46,42.1),(48,42.9),(51,43.35),(53,43.2)]:
        sample(x, edge - .75, 'shoulder_underlap')
    require(min(groups['ordinary']) > .08 and max(groups['ordinary']) < .8, 'Ordinary seam has an open or touching section')
    require(min(groups['shoulder_underlap']) > .08 and max(groups['shoulder_underlap']) < 1, 'Asymmetric underlap is not seated')
    return {name: {'samples': len(values), 'minimum_mm': min(values), 'median_mm': float(np.median(values)), 'maximum_mm': max(values)} for name, values in groups.items()}


def main():
    out = ROOT / 'build'
    out.mkdir(exist_ok=True)
    print('Building front/back/PCB in the assembled pose', flush=True)
    assembled, _, timing = build(ROOT / 'parts/ipaq_case.py')
    shapes = {c.label: c.solid for c in assembled._nurb_scene.components}
    require(set(shapes) == {'Front', 'Back', 'PCB'}, 'The combined model must have exactly Front, Back and PCB')
    require(assembled.is_valid and len(assembled.solids()) == 3, 'Invalid assembly topology')
    for name, shape in shapes.items():
        require(shape.is_valid and len(shape.solids()) == 1, f'{name} must be one valid solid')
    bores = measure_bores(shapes)
    seats = measure_seats(shapes)
    interference = measure_interference(shapes)
    seam = measure_shell_seam(shapes)
    # Negative controls prove that alignment is measured from CAD rather than copied from the datums.
    for delta in [(0.25, 0, 0), (0, 0, .25)]:
        moved = {**shapes, 'PCB': Pos(*delta) * shapes['PCB']}
        try:
            measure_bores(moved)
            measure_seats(moved)
        except AlignmentError:
            continue
        raise AlignmentError(f'The alignment check accepted a PCB displaced by {delta}')
    children = []
    colors = {'Front': (178,186,194), 'Back': (125,138,150), 'PCB': (33,102,64)}
    glb = trimesh.Scene()
    for name, shape in shapes.items():
        detached = Compound.cast(shape.wrapped)
        detached.label = name
        detached.color = Color(*(v / 255 for v in colors[name]))
        export_step(detached, out / f'{name.lower()}.step')
        require(import_step(out / f'{name.lower()}.step').is_valid, f'{name} STEP failed to read back')
        children.append(detached)
        BRepTools.Clean_s(detached.wrapped)
        mesher = BRepMesh_IncrementalMesh(detached.wrapped, .025, False, .07, True)
        mesher.Perform()
        vertices, faces, _ = _triangulate(detached, .025, remesh=False)
        mesh = trimesh.Trimesh(vertices, faces, process=False)
        mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=np.tile([*colors[name], 255], (len(mesh.vertices), 1)))
        mesh.apply_scale(.001)
        mesh.units = 'm'
        glb.add_geometry(mesh, node_name=name, geom_name=name)
    export_step(Compound(children=children, label='iPAQ front back PCB'), out / 'ipaq-case.step')
    glb.export(out / 'ipaq-case.glb')
    reread = import_step(out / 'ipaq-case.step')
    require(reread.is_valid and len(reread.solids()) == 3, 'Combined STEP must retain three valid solids')
    loaded = trimesh.load(out / 'ipaq-case.glb', force='scene')
    require(set(loaded.geometry) == set(shapes), 'GLB lost component names')
    require(np.max(abs(loaded.extents * 1000 - np.array(list(assembled.bounding_box().size)))) < .05, 'GLB unit or placement mismatch')
    # STEP is the exchange artifact. Its imported component geometry must preserve the alignment too.
    imported = {c.label: c for c in reread.children}
    require(set(imported) == set(shapes), 'STEP lost component names')
    exported_bores = measure_bores(imported)
    exported_seats = measure_seats(imported)
    exported_interference = measure_interference(imported)
    report = {'accepted': True, 'build_ms': timing, 'solid_count': 3, 'dimensions_mm': list(assembled.bounding_box().size), 'bores': bores, 'seats': seats, 'interference': interference, 'shell_seam': seam, 'negative_controls': {'pcb_shift_x_0_25_mm': 'rejected', 'pcb_shift_z_0_25_mm': 'rejected'}, 'step_readback': {'valid': True, 'bores': exported_bores, 'seats': exported_seats, 'interference': exported_interference}, 'units': {'step': 'mm', 'glb': 'm'}, 'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'case_profiles.py', *sorted((ROOT/'parts').glob('*.py'))]}, 'exports': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.step')) + sorted(out.glob('*.glb'))}, 'limits': 'CAD alignment and sampled seam checks only; physical fit and absolute scan scale remain uncalibrated. The PCB is a mechanical envelope.'}
    (out / 'assembly-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'accepted': True, 'solids': 3, 'maximum_hole_axis_error_mm': max(row['axis_error_mm'] for row in bores), 'maximum_step_hole_axis_error_mm': max(row['axis_error_mm'] for row in exported_bores), 'report': 'build/assembly-validation.json'}), flush=True)


if __name__ == '__main__':
    main()
