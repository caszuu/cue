from pygame.math import Vector3 as Vec3, Vector2 as Vec2
from ..rendering import cue_gizmos as gizmo

from .cue_entity_types import DevTickState

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
def handle_transform_edit_mode(s: dict, dev_state: DevTickState, en_data: dict, move_enabled: bool = True, rot_enabled: bool = True, scale_enabled: bool = True):
    if dev_state.edit_mode_changed:
        if dev_state.edit_mode == 0:
            # cleanup prev edit
            s.pop("pre_edit", None)

        elif dev_state.edit_mode == 1 and move_enabled: # move
            s["pre_edit"] = en_data["t_pos"]

        elif dev_state.edit_mode == -1 and move_enabled: # undo move
            en_data["t_pos"] = s["pre_edit"]
            s.pop("pre_edit")
        
        elif dev_state.edit_mode == 2 and rot_enabled: # rotate
            s["pre_edit"] = en_data["t_rot"]

        elif dev_state.edit_mode == -2 and rot_enabled: # undo rotate
            en_data["t_rot"] = s["pre_edit"]
            s.pop("pre_edit")
        
        elif dev_state.edit_mode == 3 and scale_enabled: # scale
            s["pre_edit"] = en_data["t_scale"]

        elif dev_state.edit_mode == -3 and scale_enabled: # undo scale
            en_data["t_scale"] = s["pre_edit"]
            s.pop("pre_edit")
    
    elif dev_state.edit_mode == 1 and move_enabled: # handle move
        translate_y_dir = Vec3()
        if dev_state.edit_mode_axis == 0:
            translate_x_dir = choose_axis(dev_state.view_right)
            translate_y_dir = choose_axis(dev_state.view_up)
            line_col = Vec3(.6, .6, .6)
        elif dev_state.edit_mode_axis == 1:
            translate_x_dir = Vec3(1., 0., 0.)
            line_col = Vec3(1., .35, .35)
        elif dev_state.edit_mode_axis == 2:
            translate_x_dir = Vec3(0., 1., 0.)
            line_col = Vec3(.35, 1., .35)
        else: # dev_state.edit_mode_axis == 3:
            translate_x_dir = Vec3(0., 0., -1.)
            line_col = Vec3(.35, .35, 1.)

        en_data["t_pos"] = s["pre_edit"] + translate_x_dir * .005 * dev_state.edit_mode_mouse_diff[0] + translate_y_dir * .005 * dev_state.edit_mode_mouse_diff[1]

        translate_x_dir *= 5000
        translate_y_dir *= 5000

        gizmo.draw_line(translate_x_dir + s["pre_edit"], -translate_x_dir + s["pre_edit"], line_col, line_col)
        gizmo.draw_line(translate_y_dir + s["pre_edit"], -translate_y_dir + s["pre_edit"], line_col, line_col)

    elif dev_state.edit_mode == 2 and rot_enabled: # handle rotate
        rotatation_selector_y = Vec3()
        if dev_state.edit_mode_axis == 0:
            rotatation_selector_y = choose_axis(dev_state.view_right) * -1
            rotatation_selector = choose_axis(dev_state.view_up) * -1
            line_col = Vec3(.6, .6, .6)
        elif dev_state.edit_mode_axis == 1:
            rotatation_selector = Vec3(1., 0., 0.)
            line_col = Vec3(1., .35, .35)
        elif dev_state.edit_mode_axis == 2:
            rotatation_selector = Vec3(0., -1., 0.)
            line_col = Vec3(.35, 1., .35)
        else: # dev_state.edit_mode_axis == 3:
            rotatation_selector = Vec3(0., 0., 1.)
            line_col = Vec3(.35, .35, 1.)

        en_data["t_rot"] = s["pre_edit"] + rotatation_selector * dev_state.edit_mode_mouse_diff[0] * .4 + rotatation_selector_y * dev_state.edit_mode_mouse_diff[1] * .4

        if not dev_state.edit_mode_axis == 0:
            rotatation_selector *= 5000
            gizmo.draw_line(rotatation_selector + en_data["t_pos"], -rotatation_selector + en_data["t_pos"], line_col, line_col)

    elif dev_state.edit_mode == 3 and scale_enabled: # handle scale
        if dev_state.edit_mode_axis == 0: # by default scale on all axis
            scale_vec = s["pre_edit"].normalize()
            line_col = Vec3(.6, .6, .6)
        elif dev_state.edit_mode_axis == 1:
            scale_vec = Vec3(1., 0., 0.)
            line_col = Vec3(1., .35, .35)
        elif dev_state.edit_mode_axis == 2:
            scale_vec = Vec3(0., 1., 0.)
            line_col = Vec3(.35, 1., .35)
        else: # dev_state.edit_mode_axis == 3:
            scale_vec = Vec3(0., 0., 1.)
            line_col = Vec3(.35, .35, 1.)

        en_data["t_scale"] = s["pre_edit"] + scale_vec * dev_state.edit_mode_mouse_diff[0] * .005

        if not dev_state.edit_mode_axis == 0:
            scale_vec *= 5000
            gizmo.draw_line(scale_vec + en_data["t_pos"], -scale_vec + en_data["t_pos"], line_col, line_col)