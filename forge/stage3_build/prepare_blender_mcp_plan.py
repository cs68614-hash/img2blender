#!/usr/bin/env python3
"""Compile an ObjectSculptSpec into an agent-executable Blender MCP operation plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_blender_scene import load_spec, validate_spec


def operation(op_id: str, action: str, **parameters: Any) -> dict[str, Any]:
    return {
        "id": op_id,
        "action": action,
        "parameters": parameters,
        "status": "pending",
        "evidence": None,
    }


def compile_plan(spec: dict[str, Any], spec_path: Path, blend_path: Path, render_path: Path) -> dict[str, Any]:
    validate_spec(spec)
    encoded = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    operations: list[dict[str, Any]] = [
        operation("scene.reset", "reset-scene"),
        operation(
            "scene.configure",
            "configure-scene",
            backend=spec.get("backend", {}),
            renderSettings=spec.get("renderSettings", {}),
        ),
    ]
    for material in spec.get("materials", []):
        if isinstance(material, dict) and material.get("id"):
            operations.append(operation(f"material.{material['id']}", "upsert-principled-material", material=material))
    for component in spec["componentTree"]:
        operations.append(operation(
            f"component.{component['id']}",
            "upsert-component",
            component=component,
        ))
    operations.extend([
        operation("scene.parent", "apply-component-hierarchy"),
        operation("scene.review-rig", "upsert-review-camera-and-lights", camera=spec.get("referenceCamera", {})),
        operation("scene.validate", "inspect-scene", checks=[
            "component-count", "object-names", "parent-hierarchy", "materials", "camera", "nonzero-bounds",
        ]),
        operation("scene.save", "save-blend", path=str(blend_path)),
        operation("scene.render", "render-review", path=str(render_path)),
        operation("scene.screenshot", "capture-viewport-evidence", viewpoint="review-camera"),
    ])
    return {
        "schemaVersion": 1,
        "kind": "img2blender-mcp-plan",
        "specPath": str(spec_path),
        "specSha256": hashlib.sha256(encoded).hexdigest(),
        "transport": {
            "type": "blender-mcp",
            "server": (spec.get("backend") or {}).get("mcpServer", "blender"),
            "toolBinding": "discover-at-runtime",
        },
        "outputs": {"blend": str(blend_path), "reviewRender": str(render_path)},
        "executionRules": [
            "The model must execute operations in order through Blender MCP, not claim completion from plan creation.",
            "After each mutation, record the MCP result in evidence and set status to completed or failed.",
            "On failure, stop before dependent operations and report the exact Blender/MCP error.",
            "Completion requires scene.validate, scene.save, scene.render, and scene.screenshot evidence.",
        ],
        "operations": operations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--render", type=Path, required=True)
    args = parser.parse_args(argv)
    spec = load_spec(args.spec)
    plan = compile_plan(spec, args.spec.resolve(), args.blend.resolve(), args.render.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"MCP_PLAN operations={len(plan['operations'])} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
