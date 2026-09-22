"""Mutation tests for requested movement, not only attachment invariance."""
import unittest
from build123d import Pos, Rot
import validate_reconstruction as validator


class CommandedMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shape, _, _ = validator.builder.build(validator.PART, overrides=validator.POSE)
        cls.oracle = validator.components(shape)

    def test_scan_pose_and_requested_pose(self):
        self.assertTrue(validator.commanded_pose_check(self.oracle, self.oracle, 0, 70)["accepted"])
        shape, _, _ = validator.builder.build(validator.PART, overrides={"arca_detent": 1, "carriage_position_mm": 140.0})
        self.assertTrue(validator.commanded_pose_check(validator.components(shape), self.oracle, 1, 140)["accepted"])

    def test_frozen_travel_fails(self):
        self.assertFalse(validator.commanded_pose_check(self.oracle, self.oracle, 0, 140)["accepted"])

    def test_frozen_detent_fails(self):
        self.assertFalse(validator.commanded_pose_check(self.oracle, self.oracle, 1, 70)["accepted"])

    def test_reversed_motion_fails(self):
        shape, _, _ = validator.builder.build(validator.PART, overrides={"arca_detent": 3, "carriage_position_mm": 0.0})
        self.assertFalse(validator.commanded_pose_check(validator.components(shape), self.oracle, 1, 140)["accepted"])

    def test_wrong_pivot_fails(self):
        x, y, z = validator.SCAN_PIVOT_MM
        move = Pos(x + 1, y, z) * Rot(0, 0, 90) * Pos(-x - 1, -y, -z)
        changed = {name: move * solid if name in validator.ATTACHED else solid for name, solid in self.oracle.items()}
        self.assertFalse(validator.commanded_pose_check(changed, self.oracle, 1, 70)["accepted"])

    def test_rail_motion_fails(self):
        changed = dict(self.oracle)
        changed["bottom Arca plate"] = Pos(1, 0, 0) * changed["bottom Arca plate"]
        self.assertFalse(validator.commanded_pose_check(changed, self.oracle, 0, 70)["accepted"])


if __name__ == "__main__":
    unittest.main()
