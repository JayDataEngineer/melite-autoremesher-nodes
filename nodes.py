"""melite-autoremesher-nodes — quad remesh inside ComfyUI graphs.

Wraps the vendored huxingyi/autoremesher CLI (references/autoremesher,
headless build) as a subprocess node: GLB in → trimesh GLB→OBJ (in-process)
→ autoremesher CLI (offscreen Qt) → trimesh OBJ→GLB (quads triangulated)
→ GLB in the ComfyUI output dir. Same contract as the gateway family
driver (plugins/melite-3d/families/autoremesher.ts), which retires with
the C/TS lane.

BUDGET LAW (mesh_refine convention, verbatim): resolution chain is
  explicit param > preset params > model.yaml defaults
Preset budget classes are DATA in
  plugins/melite-3d/models/3d/autoremesher/presets/<class>.yaml
Nothing resolves silently — no target_quads anywhere means a LOUD error.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import trimesh
import yaml

logger = logging.getLogger("autoremesher-nodes")

try:
    import folder_paths
except ImportError:  # standalone tooling/tests, never inside ComfyUI
    folder_paths = None


def _repo_root() -> Path:
    """Walk up from the pack until references/autoremesher exists (works
    in-tree and when symlinked into a ComfyUI install)."""
    here = Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / "references" / "autoremesher").is_dir():
            return cand
    return here


def find_binary() -> str:
    env = os.environ.get("AUTOREMESHER_BIN")
    if env and os.path.isfile(env):
        return env
    cand = _repo_root() / "references" / "autoremesher" / "build" / "autoremesher"
    if cand.is_file() and os.access(cand, os.X_OK):
        return str(cand)
    raise RuntimeError(
        "autoremesher binary not found (looked at " + str(cand) +
        "). Build it: cd references/autoremesher && mkdir build && cd build && "
        "cmake .. && make. Or set AUTOREMESHER_BIN."
    )


def presets_dir() -> Path:
    return _repo_root() / "plugins" / "melite-3d" / "models" / "3d" / "autoremesher" / "presets"


def load_presets() -> dict:
    """{class_id: params dict} from the preset yaml files (stem = id)."""
    out: dict = {}
    d = presets_dir()
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.yaml")):
        try:
            doc = yaml.safe_load(f.read_text()) or {}
            out[f.stem] = dict(doc.get("params") or {})
        except yaml.YAMLError as e:
            logger.warning("autoremesher: skipping unreadable preset %s: %s", f.name, e)
    return out


def _resolve(name: str, explicit, preset_params: dict, defaults: dict):
    if explicit is not None and explicit != 0 and explicit != "":
        return explicit
    if name in preset_params:
        return preset_params[name]
    return defaults.get(name)


def run_remesh(input_glb: str, work_dir: str, *, preset: str = "",
               target_quads: int = 0, edge_scaling: float = 0.0,
               sharp_edge: float = 0.0, adaptivity: float = 0.0,
               anisotropy: float = 0.0, timeout_ms: int = 0) -> str:
    """GLB → quad-remeshed GLB. Returns the output GLB path. Loud on every
    failure mode (missing input, missing budget, CLI error, no output)."""
    bin_path = find_binary()
    if not input_glb or not os.path.isfile(input_glb):
        raise RuntimeError(f"autoremesher: input GLB not found ({input_glb!r})")

    presets = load_presets()
    preset_params = presets.get(preset, {}) if preset else {}
    if preset and preset not in presets:
        raise RuntimeError(
            f"autoremesher: preset {preset!r} is unknown. Valid budget classes: "
            f"{sorted(presets)}."
        )
    # model.yaml defaults (explicit > preset > defaults; no silent defaults)
    defaults = {"target_quads": None, "edge_scaling": 1.0, "sharp_edge": 90.0,
                "adaptivity": 1.0, "anisotropy": 1.0, "timeout_ms": 120000}
    tq = _resolve("target_quads", target_quads, preset_params, defaults)
    if tq is None:
        raise RuntimeError(
            "autoremesher: no target_quads. Pass a preset (budget class: " +
            str(sorted(presets)) + ") or an explicit target_quads — "
            "silent defaults are banned."
        )

    os.makedirs(work_dir, exist_ok=True)
    input_obj = os.path.join(work_dir, "input.obj")
    output_obj = os.path.join(work_dir, "output.obj")
    output_glb = os.path.join(work_dir, "remeshed.glb")

    # GLB → OBJ (in-process; trimesh is a standard ComfyUI venv dep)
    mesh = trimesh.load(input_glb, force="mesh")
    mesh.export(input_obj, file_type="obj")

    args = [
        "--input", input_obj,
        "--output", output_obj,
        "--target-quads", str(int(tq)),
        "--edge-scaling", str(_resolve("edge_scaling", edge_scaling, preset_params, defaults)),
        "--sharp-edge", str(_resolve("sharp_edge", sharp_edge, preset_params, defaults)),
        "--smooth-normal", "0.0",
        "--adaptivity", str(_resolve("adaptivity", adaptivity, preset_params, defaults)),
        "--anisotropy", str(_resolve("anisotropy", anisotropy, preset_params, defaults)),
    ]
    tmo = int(_resolve("timeout_ms", timeout_ms, preset_params, defaults))
    proc = subprocess.run(
        [bin_path, *args],
        cwd=work_dir, capture_output=True, text=True,
        timeout=tmo / 1000.0,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    if proc.returncode != 0 or not os.path.isfile(output_obj):
        tail = (proc.stderr or proc.stdout or "no output")[-800:]
        raise RuntimeError(
            f"autoremesher: CLI exited {proc.returncode}"
            + ("" if os.path.isfile(output_obj) else " and wrote no OBJ")
            + f". Output tail: {tail}"
        )

    # OBJ (quads) → GLB (trimesh auto-triangulates)
    out_mesh = trimesh.load(output_obj, force="mesh")
    out_mesh.export(output_glb, file_type="glb")
    try:
        os.remove(input_obj)
        os.remove(output_obj)
    except OSError:
        pass
    logger.info("autoremesher: %s → %s (%d quads target, %d tri faces out)",
                os.path.basename(input_glb), output_glb, int(tq),
                len(out_mesh.faces))
    return output_glb


class AutoRemesher:
    """Quad-remesh a GLB (AI triangle soup → clean quad topology)."""

    @classmethod
    def INPUT_TYPES(cls):
        preset_ids = sorted(load_presets().keys())
        return {
            "required": {
                "glb_path": ("STRING", {"default": "", "multiline": False}),
                "preset": (preset_ids or ["prop"],),
                "target_quads": ("INT", {"default": 0, "min": 0, "max": 200000,
                                          "tooltip": "0 = use the preset budget"}),
                "filename_prefix": ("STRING", {"default": "autoremesher/remeshed"}),
            },
            "optional": {
                "edge_scaling": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 4.0,
                                            "tooltip": "0 = preset default"}),
                "sharp_edge": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 180.0}),
                "adaptivity": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0}),
                "anisotropy": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 4.0}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("glb_path",)
    FUNCTION = "remesh"
    CATEGORY = "melite/mesh"
    OUTPUT_NODE = True

    def remesh(self, glb_path: str, preset: str, target_quads: int,
               filename_prefix: str, edge_scaling: float = 0.0,
               sharp_edge: float = 0.0, adaptivity: float = 0.0,
               anisotropy: float = 0.0):
        if folder_paths is None:
            raise RuntimeError("AutoRemesher requires ComfyUI (folder_paths)")
        out_dir = folder_paths.get_output_directory()
        base, prefix = os.path.split(filename_prefix)
        sub = base.strip("/") if base.strip("/") else ""
        target = os.path.join(out_dir, sub)
        os.makedirs(target, exist_ok=True)
        idx = 1
        out_glb = os.path.join(target, f"{prefix}_{idx:05d}_.glb")
        while os.path.exists(out_glb):
            idx += 1
            out_glb = os.path.join(target, f"{prefix}_{idx:05d}_.glb")
        work_dir = os.path.join(target, f"work_{idx:05d}")

        result = run_remesh(glb_path, work_dir, preset=preset,
                            target_quads=target_quads,
                            edge_scaling=edge_scaling, sharp_edge=sharp_edge,
                            adaptivity=adaptivity, anisotropy=anisotropy)
        os.replace(result, out_glb)
        try:
            os.rmdir(work_dir)
        except OSError:
            pass

        rel = os.path.relpath(out_glb, out_dir)
        ui = {"file": [{"filename": os.path.basename(rel),
                        "subfolder": os.path.dirname(rel),
                        "type": "output"}]}
        return {"ui": ui, "result": (out_glb,)}


NODE_CLASS_MAPPINGS = {
    "AutoRemesher": AutoRemesher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoRemesher": "AutoRemesher (quad)",
}
