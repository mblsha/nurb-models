"""Populate portable feature contracts and native saved inspections for both models."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from nurb import builder, checks, compare, inspection
from nurb.server import Server


ROOT = Path(__file__).resolve().parent


def feature(identifier, role, center, transform, size, uncertainty, sections, group=None):
    reference = np.linalg.inv(np.asarray(transform).reshape(4,4)) @ [*center, 1]
    result = {"id": identifier, "role": role, "center_mm": list(center),
              "reference_point_mm": reference[:3].tolist(), "feature_size_mm": size,
              "uncertainty_mm": uncertainty, "configuration": "scan pose",
              "required": [role], "excluded": ["cosmetic texture", "unobserved interior details"],
              "notes": "Raw-reference annotation locates the source neighborhood. Native section plots are mesh estimates; linked exact B-rep validators provide specialized acceptance.",
              "sections": sections, "links": ["references/evidence.md"]}
    if group:
        result["symmetry_group"] = group
    return result


def plane(name, origin, normal, horizontal, offsets=(0,)):
    return {"name": name, "origin_mm": list(origin), "normal": list(normal), "x_direction": list(horizontal),
            "offsets_mm": list(offsets), "tolerance_mm": 0.0, "expected": "Review source and CAD contours at the recorded uncertainty."}


def lightseal_regions(root, transform):
    data = json.loads((root / "references/vision-pro-narrow-reference-sections.json").read_text())
    pockets = json.loads((root / "references/face-cushion-wide-pockets.json").read_text())
    seats = json.loads((root / "references/face-cushion-wide-seating-measurements.json").read_text())["stations"]
    regions = []
    for sign, label in ((1, "right"), (-1, "left")):
        mirror = np.array([sign,1,1])
        narrow = data["5"]["right"]
        sections = [plane("rim_"+key, np.array(data[key]["right"]["origin"])*mirror,
                          np.array(data[key]["right"]["tangent"])*mirror,
                          np.array(data[key]["right"]["inward"])*mirror, (-.5,0,.5)) for key in ("2","5","8","10")]
        center = (np.array(narrow["origin"])*mirror).tolist()
        regions.append({"name": "Narrow headset rim " + label,
                        "bounds_mm": {"min": [0 if sign==1 else -90,-55,5], "max": [90 if sign==1 else -.001,55,65]},
                        "feature": feature("headset-rim-"+label, "small inverse-T headset retaining lip", center, transform, .25, .45, sections, "headset-rim")})
        seat = seats["4"]
        center = (np.array(seat["seating_face_origin"])*mirror).tolist()
        sections = []
        for key in ("2","4","6","8"):
            s = seats[key]; u = np.array(s["seating_face_transverse_direction"])*mirror; v = np.array(s["seating_face_normal_toward_vision_pro"])*mirror
            sections.append(plane("seating_"+key, np.array(s["seating_face_origin"])*mirror, np.cross(u,v), u))
        regions.append({"name": "Broad cushion seat " + label,
                        "bounds_mm": {"min": [0 if sign==1 else -90,-60,-35], "max": [90 if sign==1 else -.001,60,25]},
                        "feature": feature("cushion-seat-"+label, "broad face-cushion seating surface", center, transform, 1.0, .75, sections, "cushion-seat")})
        for pocket in pockets["features"]:
            center = np.array(pocket["floor_center_mm"])*mirror
            normal = np.array(pocket["outward_normal_low_W"])*mirror
            major = np.array(pocket["major_axis"])*mirror
            sections = [plane("floor_and_opening", center, normal, major, (0,.5,1.0))]
            regions.append({"name": pocket["id"]+" cushion opening "+label,
                            "bounds_mm": {"min": (center-[9,9,5]).tolist(), "max": (center+[9,9,5]).tolist()},
                            "feature": feature("cushion-"+pocket["id"].lower()+"-"+label, "shallow closed cushion attachment recess", center.tolist(), transform,
                                               pocket["median_depth_mm"], pocket["dimension_uncertainty_mm"], sections, "cushion-"+pocket["id"].lower())})
    return regions


def neewer_regions(root, transform):
    shape,_,_ = builder.build(root / "parts/neewer_macro_slide_gm_mp2.py", overrides={"arca_detent":0,"carriage_position_mm":70.0})
    solids = {component.label:component.solid for component in shape._nurb_scene.components}
    records = [
        ("bottom Arca plate", "bottom-plate", "male Arca contact flanks interrupted at folded-foot bays", .5, .25, [plane("rail_stations", [0,0,0], [1,0,0], [0,1,0], (5,10,20,31.75,40,100,175.25,185,197.5,202))], None),
        ("fixed top Arca clamp", "fixed-jaw", "fixed female Arca engagement flank", .5, .75, [plane("jaw_stations", [103.4,0,0], [1,0,0], [0,1,0], (-18,0,18))], None),
        ("movable top Arca jaw", "moving-jaw", "movable female Arca engagement flank", .5, .75, [plane("jaw_stations", [103.4,0,0], [1,0,0], [0,1,0], (-18,0,18))], None),
        ("large focus knob", "drive-knob", "large focus knob mating envelope", .5, .5, [], None),
        ("exact outer focus sleeve", "focus-sleeve", "supplied STEP sleeve with declared CAD clearance", .05, 0, [], None),
        ("front guide rod", "front-rod", "guide rod axis", 6, .1, [plane("rod", [100,0,0], [1,0,0], [0,1,0])], "guide-rods"),
        ("rear guide rod", "rear-rod", "guide rod axis", 6, .1, [plane("rod", [100,0,0], [1,0,0], [0,1,0])], "guide-rods"),
    ]
    return [{"name": name, "component": name,
             "feature": feature(identifier, role, list(solids[name].bounding_box().center()), transform, size, uncertainty, sections, group)}
            for name,identifier,role,size,uncertainty,sections,group in records]


def prepare(project, name, make_regions, overrides):
    root = ROOT / project; path = root / "parts" / (name+".py")
    target = compare.setting(checks.settings(path))
    regions = compare.inspection_regions(make_regions(root, target["transform"]))
    compare.update_card(path, regions=regions)
    (root / "references/inspection-features.json").write_text(json.dumps(regions, indent=2)+"\n")
    server = Server(root)
    shape, params, _ = builder.build(path, overrides=overrides)
    hit = server._target_mesh(target["file"], target["units"])
    target.update(regions=regions, stamp=hit["stamp"])
    entry = {"shape":shape, "params":params, "target":target, "variant":"arca_0_deg" if overrides else None}
    for region in regions:
        center = region["feature"]["center_mm"]
        direction = [75,-110,100] if overrides else [0,-110,-110]
        state = {"mode":"overlay", "region":region["name"], "alignment":target["transform"],
                 "tolerance_mm":target["tolerance_mm"], "viewport":[1200,900],
                 "camera":{"position_mm":(np.array(center)+direction).tolist(), "target_mm":center,
                           "up":[0,0,1], "zoom":1, "height_mm":70 if overrides else 35}}
        item = inspection.save(server,path,entry,state,region["name"])
        stable = hashlib.md5((name+region["feature"]["id"]).encode()).hexdigest()
        inspection.setup_path(root,item["id"]).unlink()
        item["id"] = stable
        inspection.setup_path(root,stable).write_text(json.dumps(item,indent=2)+"\n")
    print(project, len(regions), "native feature contracts and saved setups")


if __name__ == "__main__":
    prepare("neewer-gm-mp2", "neewer_macro_slide_gm_mp2", neewer_regions, {"arca_detent":0,"carriage_position_mm":70.0})
    prepare("vision-pro-light-seal-13w", "vision_pro_light_seal_13w", lightseal_regions, {})
