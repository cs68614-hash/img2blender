import importlib.util
import json
import py_compile
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "stage3_build" / "generate_blender_scene.py"
SPEC = importlib.util.spec_from_file_location("generate_blender_scene", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(generator)


class GenerateBlenderSceneTest(unittest.TestCase):
    def sample_spec(self):
        return {
            "schemaVersion": 1,
            "materials": [{"id": "steel", "baseColor": "#336699", "roughness": 0.3, "metalness": 1}],
            "componentTree": [
                {"id": "root", "primitive": "box", "parent": None, "material": "steel",
                 "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [2, 1, 0.5]}},
                {"id": "cap", "primitive": "sphere", "parent": "root",
                 "transform": {"position": [1, 0, 0], "rotation": [0, 0, 0], "scale": [0.2, 0.2, 0.2]}},
            ],
        }

    def test_generates_compilable_blender_python(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            spec = temp / "spec.json"
            output = temp / "scene.py"
            blend = temp / "scene.blend"
            spec.write_text(json.dumps(self.sample_spec()), encoding="utf-8")
            self.assertEqual(generator.main([str(spec), "--out", str(output), "--blend", str(blend)]), 0)
            py_compile.compile(str(output), doraise=True)
            script = output.read_text(encoding="utf-8")
            self.assertIn('bpy.ops.wm.save_as_mainfile', script)
            self.assertIn('"componentTree"', script)
            self.assertFalse(blend.exists(), "generation must not pretend Blender ran without --run")

    def test_rejects_unsupported_primitive(self):
        spec = self.sample_spec()
        spec["componentTree"][0]["primitive"] = "metaball"
        with self.assertRaisesRegex(ValueError, "unsupported Blender primitive"):
            generator.validate_spec(spec)

    def test_all_declared_primitives_generate_compilable_script(self):
        spec = self.sample_spec()
        spec["componentTree"] = [
            {"id": primitive, "primitive": primitive, "parent": None,
             "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}}
            for primitive in sorted(generator.SUPPORTED_PRIMITIVES)
        ]
        generator.validate_spec(spec)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "scene.py"
            output.write_text(generator.render_script(
                spec, Path(temp) / "scene.blend", Path(temp) / "review.png",
                Path(temp) / "scene.glb", Path(temp) / "scene.fbx",
            ))
            py_compile.compile(str(output), doraise=True)
            script = output.read_text()
            self.assertIn("bpy.ops.render.render(write_still=True)", script)
            self.assertIn("ReviewCamera", script)
            self.assertIn("Principled BSDF", script)
            self.assertIn("bpy.ops.export_scene.gltf", script)
            self.assertIn("bpy.ops.export_scene.fbx", script)


if __name__ == "__main__":
    unittest.main()
