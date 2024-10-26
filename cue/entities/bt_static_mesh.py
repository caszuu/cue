from dataclasses import dataclass
from . import cue_entity_types as en

from ..components.cue_transform import Transform
from ..components.cue_model import ModelRenderer

from pygame.math import Vector3 as Vec3, Vector2 as Vec2
from ..rendering import cue_gizmos as gizmo

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

        if en_data["t_pos"] is None:
            en_data["t_pos"] = dev_state["suggested_initial_pos"]

        s = {"mesh": BtStaticMesh(en_data), "en_data": dict(en_data)}
    elif en_data != s["en_data"]:
        # update mesh
        del s["mesh"]
        s["mesh"] = BtStaticMesh(en_data)
        s["en_data"] = dict(en_data)

    if dev_state["is_selected"]:
        # handle trasnsform editing

        def choose_axis(input_vec: Vec3) -> Vec3:
            max_v = 0.
            max_i = 0

            for i, axis in enumerate(input_vec):
                max_v = max(max_v, abs(axis))
                max_i = i if max_v == abs(axis) else max_i

            vec_list = [0., 0., 0.]
            vec_list[max_i] = 1. if input_vec[max_i] >= 0. else -1.

            return Vec3(vec_list)

        edit_mode = dev_state["edit_mode"]
        if edit_mode[1]: # edit mode changed
            if edit_mode[0] == 0:
                # cleanup prev edit
                s.pop("pre_edit", None)

            elif edit_mode[0] == 1: # move
                s["pre_edit"] = en_data["t_pos"]

            elif edit_mode[0] == -1: # undo move
                en_data["t_pos"] = s["pre_edit"]
                s.pop("pre_edit")
            
            elif edit_mode[0] == 2: # rotate
                s["pre_edit"] = en_data["t_rot"]

            elif edit_mode[0] == -2: # undo rotate
                en_data["t_rot"] = s["pre_edit"]
                s.pop("pre_edit")
            
            elif edit_mode[0] == 3: # scale
                s["pre_edit"] = en_data["t_scale"]

            elif edit_mode[0] == -3: # undo scale
                en_data["t_scale"] = s["pre_edit"]
                s.pop("pre_edit")
        
        elif edit_mode[0] == 1: # handle move
            translate_y_dir = Vec3()
            if edit_mode[3] == 0:
                translate_x_dir = choose_axis(dev_state["editor_cam_right"])
                translate_y_dir = choose_axis(dev_state["editor_cam_up"])
                line_col = Vec3(.6, .6, .6)
            elif edit_mode[3] == 1:
                translate_x_dir = Vec3(1., 0., 0.)
                line_col = Vec3(1., .35, .35)
            elif edit_mode[3] == 2:
                translate_x_dir = Vec3(0., 1., 0.)
                line_col = Vec3(.35, 1., .35)
            else: # edit_mode[3] == 3:
                translate_x_dir = Vec3(0., 0., -1.)
                line_col = Vec3(.35, .35, 1.)

            en_data["t_pos"] = s["pre_edit"] + translate_x_dir * .005 * edit_mode[2][0] + translate_y_dir * .005 * edit_mode[2][1]

            translate_x_dir *= 5000
            translate_y_dir *= 5000

            gizmo.draw_line(translate_x_dir + s["pre_edit"], -translate_x_dir + s["pre_edit"], line_col, line_col)
            gizmo.draw_line(translate_y_dir + s["pre_edit"], -translate_y_dir + s["pre_edit"], line_col, line_col)

        elif edit_mode[0] == 2: # handle rotate
            rotatation_selector_y = Vec3()
            if edit_mode[3] == 0:
                rotatation_selector_y = choose_axis(dev_state["editor_cam_right"]) * -1
                rotatation_selector = choose_axis(dev_state["editor_cam_up"]) * -1
                line_col = Vec3(.6, .6, .6)
            elif edit_mode[3] == 1:
                rotatation_selector = Vec3(1., 0., 0.)
                line_col = Vec3(1., .35, .35)
            elif edit_mode[3] == 2:
                rotatation_selector = Vec3(0., -1., 0.)
                line_col = Vec3(.35, 1., .35)
            else: # edit_mode[3] == 3:
                rotatation_selector = Vec3(0., 0., 1.)
                line_col = Vec3(.35, .35, 1.)

            en_data["t_rot"] = s["pre_edit"] + rotatation_selector * edit_mode[2][0] * .4 + rotatation_selector_y * edit_mode[2][1] * .4

            if not edit_mode[3] == 0:
                rotatation_selector *= 5000
                gizmo.draw_line(rotatation_selector + en_data["t_pos"], -rotatation_selector + en_data["t_pos"], line_col, line_col)

        elif edit_mode[0] == 3: # handle scale
            if edit_mode[3] == 0: # by default scale on all axis
                scale_vec = s["pre_edit"].normalize()
                line_col = Vec3(.6, .6, .6)
            elif edit_mode[3] == 1:
                scale_vec = Vec3(1., 0., 0.)
                line_col = Vec3(1., .35, .35)
            elif edit_mode[3] == 2:
                scale_vec = Vec3(0., 1., 0.)
                line_col = Vec3(.35, 1., .35)
            else: # edit_mode[3] == 3:
                scale_vec = Vec3(0., 0., 1.)
                line_col = Vec3(.35, .35, 1.)

            en_data["t_scale"] = s["pre_edit"] + scale_vec * edit_mode[2][0] * .005

            if not edit_mode[3] == 0:
                scale_vec *= 5000
                gizmo.draw_line(scale_vec + en_data["t_pos"], -scale_vec + en_data["t_pos"], line_col, line_col)

    return s

def gen_def_data():
    return {
        "t_pos": None, # will be filled by "suggested_initial_pos"
        "t_rot": Vec3([0.0, 0.0, 0.0]),
        "t_scale": Vec3([1.0, 1.0, 1.0]),
        "a_model_mesh": "models/icosph.npz",
        "a_model_vshader": "shaders/base_cam.vert",
        "a_model_fshader": "shaders/basic_lit.frag",
    }

en.create_entity_type("bt_static_mesh", spawn_static_mesh, BtStaticMesh.despawn, dev_static_mesh, gen_def_data)

