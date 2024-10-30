from dataclasses import dataclass

from . import cue_entity_types as en

from ..components.cue_transform import Transform
from ..rendering import cue_gizmos as gizmo

from pygame.math import Vector3 as Vec3
import pygame as pg

from .cue_entity_utils import handle_transform_edit_mode

# a trigger box entity for triggering map loads / transitions

@dataclass(init=False, slots=True)
class BtMapTrigger:
    def __init__(self, en_data: dict) -> None:
        pass

    # def __del__(self) -> None:
    #     pass

    def despawn(self) -> None:
        pass # self.trigger_aabb.disable()

    trigger_aabb: None # PhysAABB

def spawn_map_trigger(en_data: dict) -> BtMapTrigger:
    return BtMapTrigger(en_data)

def dev_map_trigger(s: dict | None, dev_state: dict, en_data: dict) -> dict:
    if s is None:
        # init aabb editor

        if en_data["t_pos"] is None:
            en_data["t_pos"] = dev_state["suggested_initial_pos"]

        s = {"aabb_t": Transform(en_data["t_pos"], Vec3(0., 0., 0.), en_data["t_scale"]), "last_data": dict(en_data)}
    elif en_data != s["last_data"]:
        s["aabb_t"] = Transform(en_data["t_pos"], Vec3(0., 0., 0.), en_data["t_scale"])
        s["last_data"] = dict(en_data)

    # handle edit mode

    if dev_state["is_selected"]:
        handle_transform_edit_mode(s, dev_state, en_data)

    # draw trigger gizmo

    t = s["aabb_t"]

    min_p = t._pos - t._scale / 2
    max_p = t._pos + t._scale / 2

    line_col = Vec3(.35, .35, 1.) if dev_state["is_selected"] else Vec3(.15, .15, .6)

    gizmo.draw_box(min_p, max_p, line_col)

    return s

def gen_def_data() -> dict:
    return {
        "t_pos": None,
        "t_scale": Vec3(2., 2., 2.),
        "next_map": "",
        "enabled_at_start": True,
    }

en.create_entity_type("bt_map_trigger", spawn_map_trigger, BtMapTrigger.despawn, dev_map_trigger, gen_def_data)