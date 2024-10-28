from pygame.math import Vector3 as Vec3, Vector2 as Vec2
from ..rendering import cue_gizmos as gizmo

# snap and normalize a arbitrary vector to one of the axis (positive or negative)
def choose_axis(input_vec: Vec3) -> Vec3:
    max_v = 0.
    max_i = 0

    for i, axis in enumerate(input_vec):
        max_v = max(max_v, abs(axis))
        max_i = i if max_v == abs(axis) else max_i

    vec_list = [0., 0., 0.]
    vec_list[max_i] = 1. if input_vec[max_i] >= 0. else -1.

    return Vec3(vec_list)

# handles the edit mode for the standard Transform entity params
def handle_transform_edit_mode(s: dict, dev_state: dict, en_data: dict, move_enabled: bool = True, rot_enabled: bool = True, scale_enabled: bool = True):
    edit_mode = dev_state["edit_mode"]
    if edit_mode[1]: # edit mode changed
        if edit_mode[0] == 0:
            # cleanup prev edit
            s.pop("pre_edit", None)

        elif edit_mode[0] == 1 and move_enabled: # move
            s["pre_edit"] = en_data["t_pos"]

        elif edit_mode[0] == -1 and move_enabled: # undo move
            en_data["t_pos"] = s["pre_edit"]
            s.pop("pre_edit")
        
        elif edit_mode[0] == 2 and rot_enabled: # rotate
            s["pre_edit"] = en_data["t_rot"]

        elif edit_mode[0] == -2 and rot_enabled: # undo rotate
            en_data["t_rot"] = s["pre_edit"]
            s.pop("pre_edit")
        
        elif edit_mode[0] == 3 and scale_enabled: # scale
            s["pre_edit"] = en_data["t_scale"]

        elif edit_mode[0] == -3 and scale_enabled: # undo scale
            en_data["t_scale"] = s["pre_edit"]
            s.pop("pre_edit")
    
    elif edit_mode[0] == 1 and move_enabled: # handle move
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

    elif edit_mode[0] == 2 and rot_enabled: # handle rotate
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

    elif edit_mode[0] == 3 and scale_enabled: # handle scale
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