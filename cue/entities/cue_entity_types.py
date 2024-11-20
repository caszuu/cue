from dataclasses import dataclass
from typing import Callable, Any

from pygame.math import Vector3 as Vec3

# == Cue Entity Type System ==

# In Cue, objects in a map are called entities. All entities are of one
# of the loaded entity types. Entity types are implemented in python and
# act as the scripting layer of the engine (apart from map scripts)

# an entity type is made of the following functions:
# - spawn(en_data: dict) -> Any - always defined, called when spawning an entity of that type, returns a object that will be used as the entity state (can be `None` if not required)
#   - the `spawn` function can take any arguments it wants, when the entity is being spawned from a map file, `entity_data` from the map file will be passed as arguments
#
# - despawn(e) -> None - optional, will be called on despawn of the entity
#   - the `e` might exist longer than that if references exist to it, but it will no longer be called by the game loop
#     the entity should call `del` on all rendering objects to properly despawn the entity
#
# - dev_tick(s: Any, dev_state: dict, en_data: dict | None) -> Any - optional but recommended, this special callback will *only* be called while in an editor-like app, will be called every frame
#   - the `s` param will be the same value as the return value from last frame, if this is the first call it will be None
#     you can use this to keep a state between frames as `spawn` will *never* be called in an editor-like app
#   - the `dev_state` forwards the current state of the entity in the editor (is_selected, etc.)
#   - the `en_data` param will be filled with the current `entity_data` dict for the entity
# 
# - default_data() -> dict - always defined, called when creating a new entity in an editor, should return a new copy of default entity parameters 

# == entity type registry ==

@dataclass(slots=True)
class DevTickState:
    # edit mode

    edit_mode: int
    edit_mode_axis: int

    edit_mode_changed: bool
    edit_mode_mouse_diff: tuple[int, int] | None

    # entity

    is_entity_selected: bool
    suggested_initial_pos: Vec3

    # editor viewport

    view_pos: Vec3
    view_forward: Vec3
    view_right: Vec3
    view_up: Vec3

@dataclass(slots=True)
class EntityType:
    spawn_call: Callable[[dict], Any]
    despawn_call: Callable[[Any], None] | None

    dev_call: Callable[[Any, DevTickState, dict], Any] | None
    default_data: Callable[[], dict]

class EntityTypeRegistry:
    # entity type metadata storage
    entity_types: dict[str, EntityType] = {}
    entity_names: list[str] = []

    # quick lookup dicts

    spawn_types: dict[str, Callable] = {}
    despawn_types: dict[str, Callable] = {}

    dev_types: dict[str, Callable] = {}

# == entity type init api ==

def create_entity_type(entity_type_name: str, spawn: Callable[[dict], Any], despawn: Callable[[Any], None] | None, dev: Callable[[Any, DevTickState, dict], Any] | None, default_en_data: Callable[[], dict]):
    # validate type
    
    if entity_type_name in EntityTypeRegistry.entity_types:
        raise KeyError(f"Entity type \"{entity_type_name}\" alredy exists! All entity types must have a unique name.")

    if spawn == None:
        raise ValueError("'spawn()' entity type call must always be implemented, but is None")

    # add to registry

    et = EntityType(spawn, despawn, dev, default_en_data)
    EntityTypeRegistry.entity_types[entity_type_name] = et
    EntityTypeRegistry.entity_names.append(entity_type_name)

    EntityTypeRegistry.spawn_types[entity_type_name] = spawn
    if not despawn == None:
        EntityTypeRegistry.despawn_types[entity_type_name] = despawn
    if not dev == None:
        EntityTypeRegistry.dev_types[entity_type_name] = dev
