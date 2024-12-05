from ..rendering import cue_scene as sc
from .. import cue_utils as utils

from ..rendering.cue_batch import DrawInstance, UniformBindTypes, UniformBind
from ..cue_state import GameState
from .cue_transform import Transform

import numpy as np
import OpenGL.GL as gl 
from pygame.math import Vector3 as Vec3, Vector2 as Vec2

# a generic model rendering component shared between entities

class ModelRenderer:
    def __init__(self, en_data: dict, en_trans: Transform, target_scene: 'sc.RenderScene | None' = None) -> None:
        # load assets from preload or disk
        
        self.mesh = GameState.asset_manager.load_mesh(en_data["a_model_mesh"])
        self.pipeline = GameState.asset_manager.load_shader(en_data["a_model_vshader"], en_data["a_model_fshader"])

        self.model_textures = tuple()
        if "a_model_albedo" in en_data:
            self.model_textures = (GameState.asset_manager.load_texture(en_data["a_model_albedo"]),)

        self.shader_uniform_data = []
        if "a_model_uniforms" in en_data:
            for n, v in en_data["a_model_uniforms"].items():
                loc = gl.glGetUniformLocation(self.pipeline.shader_program, n)

                if loc == -1:
                    utils.warn(f"[ModelRenderer] failed to get uniform \"{n}\"")

                if isinstance(v, float):
                    t = UniformBindTypes.FLOAT1
                    v = np.float32(v)
                elif isinstance(v, int):
                    t = UniformBindTypes.SINT1
                    v = np.int32(v)
                elif isinstance(v, Vec2):
                    t = UniformBindTypes.FLOAT2
                    v = np.array(v, dtype=np.float32)
                elif isinstance(v, Vec3):
                    t = UniformBindTypes.FLOAT3
                    v = np.array(v, dtype=np.float32)
                else:
                    utils.error(f"[ModelRenderer] value \"{v}\" cannot be used for a gl uniform")
                    continue

                self.shader_uniform_data.append(UniformBind(t, loc, v))

        self.model_opaque = True
        if en_data.get("a_model_transparent", False):
            self.model_opaque = False

        if target_scene is None:
            target_scene = GameState.active_scene

        self.scene = target_scene
        self.draw_ins = DrawInstance(self.mesh, self.pipeline, self.model_textures, self.model_opaque, self.shader_uniform_data, en_trans)

        self.model_transform = en_trans

        # insert model into the render_scene

        self.is_visible = False
        self.show()

    def despawn(self) -> None:
        if self.is_visible:
            self.scene.remove(self.draw_ins)

    # start rendering this model if hidden
    def show(self) -> None:
        if not self.is_visible:
            self.scene.append(self.draw_ins)
            self.is_visible = True

    # stop rendering this model without deleting it (yet)
    def hide(self) -> None:
        if self.is_visible:
            self.scene.remove(self.draw_ins)
            self.is_visible = False
