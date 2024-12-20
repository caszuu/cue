from dataclasses import dataclass
from . import cue_entity_types as en

from ..components.cue_transform import Transform
from ..components.cue_model import ModelRenderer

from pygame.math import Vector3 as Vec3, Vector2 as Vec2
from .cue_entity_utils import handle_transform_edit_mode

# a simple built-in static mesh for map building

@dataclass(init=False, slots=True)
class BtStaticMesh:
    def __init__(self, en_data: dict) -> None:
        self.mesh_trans = Transform(Vec3(en_data["t_pos"]), Vec3(en_data["t_rot"]), Vec3(en_data["t_scale"]))
        self.mesh_renderer = ModelRenderer(en_data, self.mesh_trans)

    # == entity hooks ==

    @staticmethod
    def spawn(en_data: dict) -> 'BtStaticMesh':
        return BtStaticMesh(en_data)

    def despawn(self) -> None:
        self.mesh_renderer.despawn()

    # since BtStaticMesh is already static, we can simply use it directly instead of faking it for the editor
    @staticmethod
    def dev_tick(s: dict | None, dev_state: en.DevTickState, en_data: dict) -> dict:
        if s is None:
            # init mesh

            if en_data["t_pos"] is None:
                en_data["t_pos"] = dev_state.suggested_initial_pos

            s = {"mesh": BtStaticMesh(en_data), "en_data": dict(en_data)}
        elif en_data != s["en_data"]:
            # update mesh
            del s["mesh"]
            s["mesh"] = BtStaticMesh(en_data)
            s["en_data"] = dict(en_data)

        if dev_state.is_entity_selected:
            # handle trasnsform editing
            handle_transform_edit_mode(s, dev_state, en_data)

        return s

    mesh_trans: Transform
    mesh_renderer: ModelRenderer

def gen_def_data():
    return {
        "t_pos": None, # will be filled by "suggested_initial_pos"
        "t_rot": Vec3([0.0, 0.0, 0.0]),
        "t_scale": Vec3([1.0, 1.0, 1.0]),
        "a_model_mesh": "models/icosph.npz",
        "a_model_vshader": "shaders/base_cam.vert",
        "a_model_fshader": "shaders/unlit.frag",
        "a_model_albedo": "textures/def_white.png",
        "a_model_transparent": False,
        "a_model_uniforms": {},
    }

en.create_entity_type("bt_static_mesh", BtStaticMesh.spawn, BtStaticMesh.despawn, BtStaticMesh.dev_tick, gen_def_data)

