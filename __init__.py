"""melite-autoremesher-nodes — vendored autoremesher CLI as a ComfyUI node.

Subprocess isolation (resilience law): the Qt binary runs offscreen in a
child process, never dlopened — a bad remesh can only fail the node.
Conversions are in-process trimesh. Budget classes are DATA
(melite-3d presets yaml), resolution chain explicit > preset > defaults.
"""
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
