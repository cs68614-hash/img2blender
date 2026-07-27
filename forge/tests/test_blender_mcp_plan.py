import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "stage3_build" / "prepare_blender_mcp_plan.py"
SPEC = importlib.util.spec_from_file_location("prepare_blender_mcp_plan", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


class BlenderMcpPlanTest(unittest.TestCase):
    def test_plan_is_ordered_and_requires_execution_evidence(self):
        spec = {
            "backend": {"target": "blender", "executionMode": "blender-mcp", "mcpServer": "local-blender"},
            "materials": [{"id": "base", "baseColor": "#ffffff"}],
            "componentTree": [{"id": "root", "primitive": "box", "parent": None, "material": "base"}],
        }
        plan = module.compile_plan(spec, Path("spec.json"), Path("object.blend"), Path("review.png"))
        self.assertEqual(plan["transport"]["type"], "blender-mcp")
        self.assertEqual(plan["transport"]["server"], "local-blender")
        ids = [item["id"] for item in plan["operations"]]
        self.assertLess(ids.index("component.root"), ids.index("scene.validate"))
        self.assertLess(ids.index("scene.validate"), ids.index("scene.save"))
        self.assertTrue(all(item["status"] == "pending" and item["evidence"] is None for item in plan["operations"]))

    def test_cli_writes_plan_without_claiming_blender_was_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec_path = root / "spec.json"
            out = root / "plan.json"
            spec_path.write_text(json.dumps({
                "materials": [],
                "componentTree": [{"id": "root", "primitive": "sphere", "parent": None}],
            }))
            self.assertEqual(module.main([
                str(spec_path), "--out", str(out), "--blend", str(root / "out.blend"),
                "--render", str(root / "review.png"),
            ]), 0)
            plan = json.loads(out.read_text())
            self.assertEqual(plan["operations"][-1]["action"], "capture-viewport-evidence")
            self.assertFalse((root / "out.blend").exists())


if __name__ == "__main__":
    unittest.main()
