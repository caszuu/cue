from typing import Callable, Any
import pygame as pg

# == Cue Entity Type System ==

# In Cue, objects in a map are called entities. All entities are of one
# of the loaded entity types. Entity types are implemented in python and
# act as the scripting layer of the engine (apart from map scripts)

# an entity type is made of the following functions:
# - spawn(...) -> Any - always defined, called when spawning an entity of that type, returns a object that will be used as the entity state (can be `None` if not required)
#   - the `spawn` function can take any arguments it wants, when the entity is being spawned from a map file, `entity_data` from the map file will be passed as arguments
#
# - despawn(e) -> None - optional, will be called on despawn of the entity
#   - the `e` might exist longer than that if references exist to it, but it will no longer be called by the game loop
#     the entity should call `del` on all rendering objects to properly despawn the entity
#
# - tick(e) -> None - optional, gets called every frame in tick phase
#
# - event(e, ev) -> bool - optional, gets called when a `pygame` event is received
#   - the entity must first register for the event type (using `asign_event()`) to get called
#   - if returns `True`, the event is treated as processed and no other entities will receive the event (block following entities from getting the event)

# == entity type registry ==

class EntityType:
    spawn_call: Callable
    despawn_call: Callable[[Any], None] | None

    tick_call: Callable[[Any], None] | None
    event_call: Callable[[Any, pg.event.Event], None] | None

    # extra metadata
    assigned_events: list[int] = []

class EntityTypeRegistry:
    # entity type metadata storage
    entity_types: dict[str, EntityType]

    # quick lookup dicts

    spawn_types: dict[str, Callable]
    despawn_types: dict[str, Callable[[Any], None]]

    event_type_assigns: dict[str, list[int]] # dict[entity_type, list[event_type]]

# == entity type init api ==

def create_entity_type(entity_type_name: str, spawn: Callable, despawn: Callable[[Any], None] | None, tick: Callable[[Any], None] | None, event: Callable[[Any, pg.event.Event], bool] | None):
    # validate type
    
    if entity_type_name in EntityTypeRegistry.entity_types:
        raise KeyError(f"Entity type \"{entity_type_name}\" alredy exists! All entity types must have a unique name.")

    if spawn == None:
        raise ValueError("'spawn()' entity type call must always be implemented, but is None")

    # add to registry

    et = EntityType(spawn, despawn, tick, event)
    EntityTypeRegistry.entity_types[entity_type_name] = et

    EntityTypeRegistry.spawn_types[entity_type_name] = spawn
    if not despawn == None:
        EntityTypeRegistry.despawn_types[entity_type_name] = despawn

    EntityTypeRegistry.event_type_assigns[entity_type_name] = et.assigned_events # assign by-reference

def assign_events(entity_type_name: str, event_types: list[int]) -> None:
    # validate type

    et = EntityTypeRegistry.entity_type_names.get(entity_type_name)

    if et == None:
        raise KeyError(f"No entity type \"{entity_type_name}\" exists yet!")

    if et.event_call == None:
        raise KeyError(f"Event type \"{entity_type_name}\" does not implement the 'event' call!")

    # assign event

    for ev in event_types:
        et.assigned_events.append(ev)
        # EventTypeRegistry.event_type_assigns update too due to it being a refrence
