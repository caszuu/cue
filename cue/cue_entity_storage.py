from .entities.cue_entity_types import EntityTypeRegistry
from typing import Any, Callable

# == Cue Entity System ==

class EntityStorage:

    def __init__(self) -> None:
        self.entity_storage = {}

        self.active_tick_calls = {}
        self.active_event_calls = {}

    def reset(self) -> None:
        for en in self.entity_storage:
            en_despawn = EntityTypeRegistry.despawn_types[en[0]]
            en_despawn(en)

        self.active_tick_calls.clear()
        self.active_event_calls.clear()

    # == entity api ==

    def spawn(self, type_name: str, name: str, **kwargs) -> Any:
        try: en_type = EntityTypeRegistry.entity_types[type_name]
        except KeyError: raise KeyError(f"Entity type named \"{type_name}\" does not exist!")

        # spawn entity

        if name in self.entity_storage:
            raise KeyError(f"Entity named \"{name}\" already exists, entities must have a unique name!")

        en_handle = en_type.spawn_call(kwargs)
        self.entity_storage[name] = (type_name, en_handle)

        # setup entity calls

        self.active_tick_calls[name] = (en_type.tick_call, en_handle)

        for event_type in en_type.assigned_events:
            self.active_event_calls.setdefault(event_type, {})[name] = (en_type.event_call, en_handle)

        return en_handle

    def despawn(self, name: str) -> None:
        try: en = self.entity_storage.pop(name)
        except KeyError: raise KeyError(f"Entity named \"{name}\" does not exist!")

        # unlink entity calls

        self.active_tick_calls.pop(name)
        
        for event_type in EntityTypeRegistry.event_type_assigns[en[0]]:
            self.active_event_calls.pop(name)

        # despawn entity
       
        en_despawn = EntityTypeRegistry.despawn_types[en[0]]
        en_despawn(en)

    def get_entity(self, expected_type_name: str, name: str) -> Any:
        try: en = self.entity_storage[name]
        except KeyError: raise KeyError(f"Entity named \"{name}\" does not exist!")
        
        if not en[0] == type_name:
            raise TypeError(f"Entity \"{name}\" found but is a wrong type \"{en[0]}\"!")
        
        return en[1]

    def get_type_of(self, name: str) -> None:
        return self.entity_storage[name][0]

    # == game loop api ==

    def process_tick(self) -> None:
        for e in self.active_entity_calls.values():
            e[0](e[1])

    def process_event(self, ev) -> bool:
        ev_calls = self.active_entity_calls.get(ev.type)

        if ev_calls == None:
            return False

        for ev_call in ev_calls.values():
            if ev_call[0](ev_call[1], ev):
                return True

        return False

    entity_storage: dict[str, tuple[str, Any]] # dict[entity_name, tuple[type_name, entity_handle]]

    # PERF TODO: bind entity state to its callable (using deepcopy)
    active_tick_calls: dict[str, tuple[Callable, Any]]
    active_event_calls: dict[int, dict[str, tuple[Callable, Any]]] # dict[event_type, dict[entity_name, tuple[event_call, entity_handle]]]
