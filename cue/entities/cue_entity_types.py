from dataclasses import dataclass
from typing import Callable, Any
import pygame as pg

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
# - dev_tick(s: Any, en_data: dict | None) -> Any - optional but recommended, this special callback will *only* be called while in an editor-like app, will be called every frame
#   - the `s` param will be the same value as the return value from last frame, if this is the first call it will be None
#     you can use this to keep a state between frames as `spawn` will *never* be called in an editor-like app
#   - the `en_data` param will be filled with the current `entity_data` dict for the entity

# == entity type registry ==

@dataclass(slots=True)
class EntityType:
    spawn_call: Callable[[dict], Any]
    despawn_call: Callable[[Any], None] | None

    dev_call: Callable[[Any, dict], Any] | None

class EntityTypeRegistry:
    # entity type metadata storage
    entity_types: dict[str, EntityType] = {}

    # quick lookup dicts

    spawn_types: dict[str, Callable] = {}
    despawn_types: dict[str, Callable] = {}

    dev_types: dict[str, Callable] = {}

# == entity type init api ==

def create_entity_type(entity_type_name: str, spawn: Callable[[dict], Any], despawn: Callable[[Any], None] | None, dev: Callable[[Any, dict], Any] | None):
    # validate type
    
    if entity_type_name in EntityTypeRegistry.entity_types:
        raise KeyError(f"Entity type \"{entity_type_name}\" alredy exists! All entity types must have a unique name.")

    if spawn == None:
        raise ValueError("'spawn()' entity type call must always be implemented, but is None")

    # add to registry

    et = EntityType(spawn, despawn, dev)
    EntityTypeRegistry.entity_types[entity_type_name] = et

    EntityTypeRegistry.spawn_types[entity_type_name] = spawn
    if not despawn == None:
        EntityTypeRegistry.despawn_types[entity_type_name] = despawn
    if not dev == None:
        EntityTypeRegistry.dev_types[entity_type_name] = dev
