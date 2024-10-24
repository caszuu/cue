from dataclasses import dataclass
from . import cue_entity_types as en

from ..components.cue_transform import Transform
from ..components.cue_model import ModelRenderer

from pygame.math import Vector3 as Vec3

# a simple built-in static mesh for map building

@dataclass(init=False, slots=True)
class BtStaticMesh:
    def __init__(self, en_data: dict) -> None:
        self.mesh_trans = Transform(Vec3(en_data["t_pos"]), Vec3(en_data["t_rot"]), Vec3(en_data["t_scale"]))
        self.mesh_renderer = ModelRenderer(en_data, self.mesh_trans)

    # def __del__(self) -> None:
    #     pass

    def despawn(self) -> None:
        self.mesh_renderer.hide() # hide until this class gets garbage collected

    mesh_trans: Transform
    mesh_renderer: ModelRenderer

def spawn_static_mesh(en_data: dict) -> BtStaticMesh:
    return BtStaticMesh(en_data)

# since BtStaticMesh is already static, we can simply use it directly instead of faking it for the editor
def dev_static_mesh(s: dict | None, dev_state: dict, en_data: dict) -> dict:
    if s is None:
        # init mesh
        s = {"mesh": BtStaticMesh(en_data), "en_data": dict(en_data)}
    elif en_data != s["en_data"]:
        # update mesh
        del s["mesh"]
        s["mesh"] = BtStaticMesh(en_data)
        s["en_data"] = dict(en_data)

    return s

def gen_def_data():
    return {
        "t_pos": Vec3([0.0, 0.0, 0.0]),
        "t_rot": Vec3([0.0, 0.0, 0.0]),
        "t_scale": Vec3([1.0, 1.0, 1.0]),
        "a_model_mesh": "models/icosph.npz",
        "a_model_vshader": "shaders/base_cam.vert",
        "a_model_fshader": "shaders/basic_lit.frag",
    }

en.create_entity_type("bt_static_mesh", spawn_static_mesh, BtStaticMesh.despawn, dev_static_mesh, gen_def_data)

