from dataclasses import dataclass
from . import cue_entity_types as en

from ..components.cue_transform import Transform
from ..rendering import cue_gizmos as gizmo

from pygame.math import Vector3 as Vec3
import pygame as pg

from .cue_entity_utils import handle_transform_edit_mode

# a simple built-in Axis Aligned Bounding Box entity usually used for world colliders

class PhysAABB:
    def disable(self):
        pass

@dataclass(init=False, slots=True)
class BtPhysAABB:
    def __init__(self, en_data: dict) -> None:
        pass # self.en_aabb
    
    # def __del__(self) -> None:
    #     pass

    def despawn(self) -> None:
        self.en_aabb.disable()
    
    en_trans: Transform
    en_aabb: PhysAABB

def spawn_phys_aabb(en_data: dict) -> BtPhysAABB:
    return BtPhysAABB(en_data)

# dev tick and aabb editor

def dev_phys_aabb(s: dict | None, dev_state: dict, en_data: dict) -> dict:
    if s is None:
        # init aabb editor

        if en_data["t_pos"] is None:
            en_data["t_pos"] = dev_state["suggested_initial_pos"]

        s = {"aabb_t": Transform(en_data["t_pos"], Vec3(0., 0., 0.), en_data["t_scale"]), "last_data": dict(en_data)}
    elif en_data != s["last_data"]:
        s["aabb_t"] = Transform(en_data["t_pos"], Vec3(0., 0., 0.), en_data["t_scale"])
        s["last_data"] = dict(en_data)

    # user input

    if dev_state["is_selected"]:
        handle_transform_edit_mode(s, dev_state, en_data, True, False, True)

    # draw aabb gizmo

    t = s["aabb_t"]

    min_p = t._pos - t._scale / 2
    max_p = t._pos + t._scale / 2

    line_col = Vec3(.55, 1., .35) if dev_state["is_selected"] else Vec3(.2, .5, .05)

    gizmo.draw_box(min_p, max_p, line_col)

    return s

def gen_def_data():
    return {
        "t_pos": None, # will be filled by "suggested_initial_pos"
        "t_scale": Vec3(1., 1., 1.),
        "phys_bitmask": 0,
    }

en.create_entity_type("bt_phys_aabb", spawn_phys_aabb, BtPhysAABB.despawn, dev_phys_aabb, gen_def_data)