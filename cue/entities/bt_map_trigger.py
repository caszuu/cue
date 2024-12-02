from dataclasses import dataclass
from . import cue_entity_types as en
from ..cue_state import GameState

from ..components.cue_transform import Transform
from ..phys.cue_phys_types import PhysAABB

from ..rendering import cue_gizmos as gizmo
from .. import cue_map

from pygame.math import Vector3 as Vec3
from .cue_entity_utils import handle_transform_edit_mode

# a trigger box entity for triggering map loads / transitions

@dataclass(init=False, slots=True)
class BtMapTrigger:
    def __init__(self, en_data: dict) -> None:
        self.aabb = PhysAABB.make(en_data["t_pos"], en_data["t_scale"], self)
        GameState.trigger_scene.add_coll(self.aabb)
        
        self.next_map = en_data["next_map"]
        self.is_enabled = en_data["enabled_at_start"]

    def on_triggered(self) -> None:
        if self.is_enabled:
            cue_map.load_map_when_safe(self.next_map)

    # == entity hooks ==

    @staticmethod
    def spawn(en_data: dict) -> 'BtMapTrigger':
        return BtMapTrigger(en_data)

    def despawn(self) -> None:
        GameState.trigger_scene.remove_coll(self.aabb)

    @staticmethod
    def dev_tick(s: dict | None, dev_state: en.DevTickState, en_data: dict) -> dict:
        if s is None:
            # init aabb editor

            if en_data["t_pos"] is None:
                en_data["t_pos"] = dev_state.suggested_initial_pos

            s = {"aabb_t": Transform(en_data["t_pos"], Vec3(0., 0., 0.), en_data["t_scale"]), "last_data": dict(en_data)}
        elif en_data != s["last_data"]:
            s["aabb_t"] = Transform(en_data["t_pos"], Vec3(0., 0., 0.), en_data["t_scale"])
            s["last_data"] = dict(en_data)

        # handle edit mode

        if dev_state.is_entity_selected:
            handle_transform_edit_mode(s, dev_state, en_data)

        # draw trigger gizmo

        t = s["aabb_t"]

        min_p = t._pos - t._scale / 2
        max_p = t._pos + t._scale / 2

        line_col = Vec3(.35, .35, 1.) if dev_state.is_entity_selected else Vec3(.15, .15, .6)
        gizmo.draw_box(min_p, max_p, line_col)

        return s

    aabb: PhysAABB

    next_map: str
    is_enabled: bool

def gen_def_data() -> dict:
    return {
        "t_pos": None,
        "t_scale": Vec3(2., 2., 2.),
        "next_map": "",
        "enabled_at_start": True,
    }

en.create_entity_type("bt_map_trigger", BtMapTrigger.spawn, BtMapTrigger.despawn, BtMapTrigger.dev_tick, gen_def_data)