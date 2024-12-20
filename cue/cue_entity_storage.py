from .entities.cue_entity_types import EntityTypeRegistry
from typing import Any, Callable

# import built-in types
from .entities import built_in_manifest

# == Cue Entity System ==

class EntityStorage:

    def __init__(self) -> None:
        self.entity_storage = {}

    def reset(self) -> None:
        for en in self.entity_storage:
            en_despawn = EntityTypeRegistry.despawn_types.get(en[0], lambda e: None)
            en_despawn(en)
        
        self.entity_storage = {}

    # == entity api ==

    def spawn(self, type_name: str, name: str, en_data: dict) -> Any:
        try: en_type = EntityTypeRegistry.entity_types[type_name]
        except KeyError: raise KeyError(f"Entity type named \"{type_name}\" does not exist!")

        # spawn entity

        if name in self.entity_storage:
            raise KeyError(f"Entity named \"{name}\" already exists, entities must have a unique name!")

        en_data.setdefault("bt_en_name", name)

        en_handle = en_type.spawn_call(en_data)
        self.entity_storage[name] = (type_name, en_handle)

        return en_handle

    def despawn(self, name: str) -> None:
        try: en = self.entity_storage.pop(name)
        except KeyError: raise KeyError(f"Entity named \"{name}\" does not exist!")

        # despawn entity

        en_despawn = EntityTypeRegistry.despawn_types[en[0]]
        en_despawn(en[1])

    def get_entity(self, expected_type_name: str, name: str) -> Any:
        try: en = self.entity_storage[name]
        except KeyError: raise KeyError(f"Entity named \"{name}\" does not exist!")
        
        if not en[0] == expected_type_name:
            raise TypeError(f"Entity \"{name}\" found but is a wrong type \"{en[0]}\"!")
        
        return en[1]

    def get_type_of(self, name: str) -> str:
        return self.entity_storage[name][0]

    entity_storage: dict[str, tuple[str, Any]] # dict[entity_name, tuple[type_name, entity_handle]]
