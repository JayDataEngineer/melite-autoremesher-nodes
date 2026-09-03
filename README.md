# melite-autoremesher-nodes

Quad remeshing inside ComfyUI graphs — Phase 0 of the consolidation plan.

**AutoRemesher** node: `glb_path` (+ `preset` budget class or explicit
`target_quads`) → clean quad-topology GLB in the output dir.

- Binary: vendored clone `references/autoremesher/build/autoremesher`
  (override: `AUTOREMESHER_BIN`), subprocess with `QT_QPA_PLATFORM=offscreen`.
- Conversions GLB↔OBJ: in-process trimesh (standard ComfyUI dep).
- Budget law verbatim from the gateway family: explicit > preset >
  defaults; no `target_quads` anywhere → LOUD error. Preset classes are
  data: `plugins/melite-3d/models/3d/autoremesher/presets/*.yaml`
  (rock 5K / prop 10K / large_prop 20K / creature 20K / complex_creature
  50K / hero 80K).
- Quad fidelity: GLB/glTF is triangles-only — the quad edge flow survives
  triangulation; export OBJ for true quads (future node if needed).

Retirement target: the gateway `type: autoremesher` family driver
(plugins/melite-3d/families/autoremesher.ts) retires once graphs consume
this node (plan Phase 2).
