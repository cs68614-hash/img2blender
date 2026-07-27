# img2blender migration plan

## Decision

Treat Blender as a **new rendering/build backend**, not as a search-and-replace of “Three.js”. The
existing intake, evidence, sculpt-spec, pass orchestration, and image-comparison stages contain the
valuable domain logic. Rewriting them would add risk without improving Blender output.

The spelling is **img2blender**. `img2blener` is not used as an alias because publishing two skill
names would make installation, invocation, and future package discovery ambiguous.

## Current state

| Layer | Keep | Change |
| --- | --- | --- |
| Image intake and evidence | Image probing, detail inventory, camera evidence, PBR evidence | Add Blender colour-management metadata where needed |
| Sculpt specification | Components, transforms, materials, pivots, acceptance criteria | Move runtime-specific fields behind a backend section |
| Pass orchestration | Locked passes and review decisions | Make generated artifact type backend-aware |
| Build | Spec-to-code workflow | Blender Python generator is now primary; Three.js remains legacy-only |
| Review | Reference/render comparison and per-feature gates | Fixed-camera Blender PNG is implemented; orbit packaging remains |
| Delivery | Generated source | `.blend`, preview PNG, and optional glTF/FBX exports are implemented |

## Target command boundary

The user-facing workflow should converge on:

```bash
python3 forge/next.py object-sculpt-spec.json
python3 forge/stage3_build/prepare_blender_mcp_plan.py object-sculpt-spec.json \
  --out build/mcp-plan.json --blend build/object.blend --render build/review.png
```

The agent must then discover the locally configured Blender MCP tools and execute the plan against
the live Blender session. Each operation remains `pending` until an MCP result is attached as
evidence. The `.blend`, review render, and viewport screenshot—not plan creation—prove completion.
`generate_blender_scene.py` remains available for CI/headless environments without MCP.

## Backend contract

Introduce `spec.backend` without breaking existing specs:

```json
{
  "backend": {
    "target": "blender",
    "executionMode": "blender-mcp",
    "mcpServer": "blender",
    "blenderVersion": "4.x",
    "renderEngine": "BLENDER_EEVEE_NEXT",
    "unitSystem": "METRIC"
  }
}
```

During migration, a missing backend means `threejs` for old specs and `blender` for newly created
specs. Validation must print the resolved backend so a compatibility run cannot be mistaken for a
Blender run.

## Milestones

### 0. Identity and honesty *(shipped)*

- Rename the skill and public documentation to `img2blender`.
- Keep historical release, gallery, and source links intact.
- Clearly label the current Three.js generator as a compatibility backend.

### 1. Minimal Blender scene *(shipped)*

- [x] Generate an inspectable Blender Python build script from `componentTree` and `materials`.
- [x] Generate supported primitives, hierarchy, transforms, and Principled BSDF materials.
- [x] Save a deterministic `.blend` from Blender background mode via `--run`.
- [x] Test generation and Python syntax without requiring Blender in the unit-test environment.
- [ ] Add a backend-neutral intermediate scene representation.
- [x] Add spec-driven review camera defaults, three-point lighting, and optional PNG rendering.
- [ ] Add an integration fixture that runs when Blender is available.

### 2. Fidelity features *(initial coverage shipped)*

- [x] Map every declared primitive family to Blender scene geometry (with conservative fallback
  profiles where the spec does not yet carry backend-neutral control points).
- [ ] Map projected textures and procedural surface frequency bands to Blender nodes.
- Define explicit conversions for Three.js roughness/metalness conventions and Blender colour
  spaces instead of copying numeric settings blindly.
- Reproduce review cameras and framing within an agreed pixel tolerance.

### 3. Blender-native review *(initial fixed-view render shipped)*

- [x] Render a fixed review view headlessly with `--render ... --run`.
- [ ] Render and package orbit review views.
- Feed those renders into the existing comparison, feature, and geometry-integrity gates.
- Record Blender version, renderer, device, seed, and colour-management settings in evidence.

### 4. Compatibility retirement

- Run representative fixtures through both backends during a deprecation window.
- Remove Three.js from the default path only after Blender covers all supported primitives and
  review gates.
- Keep a tagged legacy branch or release rather than maintaining two permanent product identities.

## Definition of done

The rename is technically complete only when all of the following are true:

1. A fresh `/img2blender` run creates a valid `.blend` without invoking the Three.js generator.
2. The file opens in the supported Blender LTS/current version with no missing textures.
3. Fixed-camera and orbit renders run in background mode and enter the existing review loop.
4. Materials, hierarchy, object names, units, pivots, and export metadata are validated.
5. Documentation no longer presents the compatibility backend as the primary workflow.

## What not to do

- Do not rename `generate_threejs_factory.py` while it still emits TypeScript; that hides rather
  than removes the coupling.
- Do not globally replace technical terms such as `MeshPhysicalMaterial` with Blender names.
- Do not delete historical URLs or changelog links merely because they contain `img2threejs`.
- Do not make `.blend` binaries the sole implementation artifact; generated Python must remain
  reviewable and reproducible.
