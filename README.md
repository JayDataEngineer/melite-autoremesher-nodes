# melite-autoremesher-nodes

Quad remeshing inside ComfyUI graphs — Phase 0 of the consolidation plan.

**AutoRemesher** node: `glb_path` (+ `preset` budget class or explicit
`target_quads`) → clean quad-topology GLB in the output dir.

- Binary: pack-owned. `install.py` (run by ComfyUI-Manager on
  install) fetches + sha-verifies the pinned release asset
  `autoremesher-d9ef96bd` from this repo's releases into
  `native/autoremesher`; `find_binary()` resolves it there
  (override: `AUTOREMESHER_BIN` pointing at a binary you built).
  Subprocess with `QT_QPA_PLATFORM=offscreen`.
- Conversions GLB↔OBJ: in-process trimesh (standard ComfyUI dep).
- Budget law verbatim from the gateway family: explicit > preset >
  defaults; no `target_quads` anywhere → LOUD error. Preset classes are
  data: `presets/*.yaml` in this pack
  (rock 5K / prop 10K / large_prop 20K / creature 20K / complex_creature
  50K / hero 80K).
- Quad fidelity: GLB/glTF is triangles-only — the quad edge flow survives
  triangulation; export OBJ for true quads (future node if needed).

## Install

Install through ComfyUI-Manager (git URL
`https://github.com/JayDataEngineer/melite-autoremesher-nodes`).
Manager runs `install.py`, which converges the binary — no estate
tooling, no environment variables, nothing external. A manual clone
converges the same way by running `python install.py`.

Retirement target: the gateway `type: autoremesher` family driver
(plugins/melite-3d/families/autoremesher.ts) retires once graphs consume
this node (plan Phase 2).
