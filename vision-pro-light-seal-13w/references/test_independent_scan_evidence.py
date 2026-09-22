"""Independent contour extraction must follow measured geometry, not ideal dimensions."""
import unittest
import numpy as np
import trimesh
from scipy.spatial import cKDTree
import independent_scan_evidence as evidence


def scanned_slot(shift=0):
    values = np.linspace(-9,9,181)
    u,v = np.meshgrid(values, values)
    # An 8 by 4 mm obround cut into a planar support, sampled as a noisy-free scan.
    distance = np.hypot(np.maximum(np.abs(u-shift)-2,0),v)
    depth = -np.clip((2.2-distance)/.4,0,1)
    vertices = np.column_stack((u.ravel(),v.ravel(),depth.ravel()))
    index = np.arange(len(values)**2).reshape(len(values),len(values))
    a=index[:-1,:-1].ravel();b=index[:-1,1:].ravel();c=index[1:,:-1].ravel();d=index[1:,1:].ravel()
    return trimesh.Trimesh(vertices=vertices, faces=np.vstack((np.column_stack((a,b,c)),np.column_stack((b,d,c)))), process=False)


class IndependentExtraction(unittest.TestCase):
    feature = {"floor_center_mm":[0,0,-1],"outward_normal_low_W":[0,0,1],"major_axis":[1,0,0],"dimension_uncertainty_mm":.4}

    def test_recovers_raw_slot_boundary(self):
        result=evidence.extract_pocket(scanned_slot(),self.feature,1)
        self.assertEqual(result["status"],"measured")
        self.assertTrue(np.allclose(result["bounds_mm"],[8.2,4.2],atol=.2),result["bounds_mm"])

    def test_authored_slot_dimensions_cannot_move_reference(self):
        mesh=scanned_slot()
        original=evidence.extract_pocket(mesh,self.feature,1)
        altered=evidence.extract_pocket(mesh,{**self.feature,"depressed_floor_length_mm":100,"depressed_floor_width_mm":100},1)
        self.assertEqual(original["contour_local_uv_mm"],altered["contour_local_uv_mm"])

    def test_shifted_scan_is_not_mirrored_or_fitted_back(self):
        original=evidence.extract_pocket(scanned_slot(),self.feature,1)
        shifted=evidence.extract_pocket(scanned_slot(.8),self.feature,1)
        points=np.asarray(original["contour_local_uv_mm"])
        moved=np.asarray(shifted["contour_local_uv_mm"])
        self.assertGreater(np.quantile(cKDTree(points).query(moved)[0],.95),.5)

    def test_missing_surface_is_not_accepted(self):
        mesh=scanned_slot()
        mesh.vertices[:,2]=0
        with self.assertRaisesRegex(ValueError,"no geometry-supported"):
            evidence.extract_pocket(mesh,self.feature,1)


if __name__ == "__main__":
    unittest.main()
