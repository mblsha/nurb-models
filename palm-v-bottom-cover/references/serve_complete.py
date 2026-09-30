#!/usr/bin/env python3
"""Run the normal NURB viewer, initially building only palm_v_complete.

Usage: python serve_complete.py PROJECT_ROOT [--port 7375]

The existing viewer tab can reconnect to the same port. Open its normal route
/?part=palm_v_complete to request the current published model without rebuilding.
GET /glb/palm_v_complete.glb retrieves those same cached display bytes after the
initial build. This is an in-memory cache, not a loader for exported GLB files.
Source saves, sliders, checks, reference comparison and exports use NURB's normal
watcher and command handling. A shared-source save can still rebuild other parts.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from pathlib import Path
import signal
import sys


def install_absolute_display_meshing(accuracy: float, angular: float, frame_angular: float = 0.08) -> None:
    """Use absolute tessellation and native surface normals in this process only."""
    import inspect
    import numpy as np
    import trimesh
    from nurb import builder
    from OCP.BRep import BRep_Tool
    from OCP.BRepLib import BRepLib_ToolTriangulatedShape
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_Orientation
    from OCP.TopLoc import TopLoc_Location

    original = builder._triangulate
    if "remesh" not in inspect.signature(original).parameters:
        raise RuntimeError("This viewer adapter requires NURB's remesh-aware triangulator")

    def triangulate(shape, tolerance, up=(0, 0, 1), *, remesh=True):
        if remesh:
            # Server stats clear OCCT's cache; mesh here, after that calculation.
            BRepTools.Clean_s(shape.wrapped)
            # component() preserves this label on the solid passed to to_mesh.
            # The long channel surfaces need closer angular sampling for shading.
            angle = frame_angular if getattr(shape, "label", "") == "Smooth paired stylus channels" else angular
            mesher = BRepMesh_IncrementalMesh(shape.wrapped, accuracy, False, angle, True)
            if not mesher.IsDone():
                raise RuntimeError("Absolute display tessellation did not complete")
        return original(shape, tolerance, up, remesh=False)

    def to_mesh(shape, tolerance=0.1, up=(0, 0, 1)):
        points, faces, colors = triangulate(shape, tolerance, up)
        normals = []
        for face in shape.faces():
            location = TopLoc_Location()
            poly = BRep_Tool.Triangulation_s(face.wrapped, location)
            if poly is None:
                continue
            BRepLib_ToolTriangulatedShape.ComputeNormals_s(face.wrapped, poly)
            transform = location.Transformation()
            sign = -1 if face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED else 1
            for index in range(1, poly.NbNodes() + 1):
                normal = poly.Normal(index).Transformed(transform)
                normals.append((sign * normal.X(), sign * normal.Y(), sign * normal.Z()))
        if len(normals) != len(points):
            raise RuntimeError("Native display normals do not match the tessellation nodes")
        # glTF stores positions as float32. Omit only triangles that have exactly
        # zero area at that precision, keeping face seams and every other facet.
        vertices = np.asarray(points, dtype=np.float32).astype(np.float64).reshape(-1, 3)
        triangles = np.asarray(faces, dtype=np.int64).reshape(-1, 3)
        corners = vertices[triangles]
        area_vectors = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
        triangles = triangles[np.any(area_vectors != 0, axis=1)]
        return trimesh.Trimesh(
            vertices=vertices,
            faces=triangles,
            vertex_colors=np.asarray(colors, dtype=np.uint8).reshape(-1, 4),
            vertex_normals=np.asarray(normals, dtype=np.float64).reshape(-1, 3),
            process=False,
        )

    builder._triangulate = triangulate
    builder.to_mesh = to_mesh


async def run(root: Path, port: int, accuracy: float, angular: float, frame_angular: float) -> None:
    from nurb.server import Server
    from websockets.asyncio.server import serve

    install_absolute_display_meshing(accuracy, angular, frame_angular)
    server = Server(root, port=port, draft=False, open_browser=False)
    server.loop = asyncio.get_running_loop()
    server.queue = asyncio.Queue()
    stopped = asyncio.Event()
    installed_signals = []
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            server.loop.add_signal_handler(signum, stopped.set)
            installed_signals.append(signum)
        except (NotImplementedError, RuntimeError):
            pass

    stop_task = None
    try:
        server.watch()
        server.drain_task = asyncio.create_task(server.drain())
        server.queue.put_nowait(str(root / "parts" / "palm_v_complete.py"))
        async with serve(
            server.ws,
            "127.0.0.1",
            server.port,
            process_request=server.http,
            origins=server.origins,
            open_timeout=None,
            max_size=70 * 1024 * 1024,
        ):
            base = f"http://127.0.0.1:{server.port}"
            print(f"NURB viewer: {base}/?part=palm_v_complete", flush=True)
            print(f"Current display mesh after build: {base}/glb/palm_v_complete.glb", flush=True)
            print("Initial queue: palm_v_complete only. Normal source watching is active.", flush=True)
            print(f"Display mesh: absolute {accuracy} mm, {angular} radians ({frame_angular} for channels), native surface normals.", flush=True)
            stop_task = asyncio.create_task(stopped.wait())
            done, _ = await asyncio.wait(
                (stop_task, server.drain_task), return_when=asyncio.FIRST_COMPLETED
            )
            if server.drain_task in done:
                await server.drain_task
    finally:
        if server.observer is not None:
            server.observer.stop()
            await asyncio.to_thread(server.observer.join, 5)
        for task in (stop_task, server.drain_task):
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        for signum in installed_signals:
            server.loop.remove_signal_handler(signum)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--port", type=int, default=7375)
    parser.add_argument("--accuracy-mm", type=float, default=0.025)
    parser.add_argument("--angular-rad", type=float, default=0.18)
    parser.add_argument("--frame-angular-rad", type=float, default=0.08)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    if not (root / "parts" / "palm_v_complete.py").is_file():
        parser.error(f"Expected published source: {root / 'parts' / 'palm_v_complete.py'}")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    if not 0.001 <= args.accuracy_mm <= 0.1 or not all(0.01 <= angle <= 0.3 for angle in (args.angular_rad, args.frame_angular_rad)):
        parser.error("Use an accuracy from 0.001 to 0.1 mm and angle from 0.01 to 0.3 radians")
    try:
        asyncio.run(run(root, args.port, args.accuracy_mm, args.angular_rad, args.frame_angular_rad))
    except KeyboardInterrupt:
        pass
    except OSError as error:
        print(f"Cannot start viewer on port {args.port}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
