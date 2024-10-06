import json
import copy
import os
from typing import Any

from .cue_state import GameState

from .entities.cue_entity_types import EntityTypeRegistry
from .cue_entity_storage import EntityStorage

from pygame.math import Vector3 as Vec3, Vector2 as Vec2

# from .cue_asset_manager import AssetManager

# == Cue Map Format and Loader ==

# Cue Map Files are json files describing an initial state of a map and it's metadata (entity types used, assets used)
#
# The json is formated as follows:
# {
#     "cmf_ver": 1,
#     "cmf_header": {
#         "type_list": [ // entity types used in this map file
#             "bt_example_radio",
#             "bt_model_static",
#             "bt_model_dynamic",
#         ],
#         "asset_list": [ // assets which are used in this map file, should be loaded while in a loading screen
#             "assets/models/big_door.pkl",
#         ]
#     },
#     "cmf_data": {
#         "map_entities": [
#             {
#                 "en_name": "pt_main_door",
#                 "en_type": "bt_model_static",
#                 "en_data": {
#                     "trans_pos": [0, 1, 2],
#                     "trans_rot": [.561, .210, .135],
#                     "start_open": true,
#                     "model_asset": "str:assets/models/big_door.pkl",
#                 }
#             },
#             {
#                 "en_name": "pt_second_door",
#                 "en_type": "bt_model_static",
#                 "en_data": {
#                     "trans_pos": [0, 1, 2],
#                     "trans_rot": [.561, .210, .135],
#                     "start_open": 1,
#                     "model_asset": null,
#                 }
#             }
#         ]
#     }
# }

# == Map Parser ==

MAP_LOADER_VERSION = 1

# loads and parses a map file into EntityStorage and AssetManager, this function should be called within a "loading screen" context
def load_map(file_path: str) -> None:    
    # read the map file
    
    with open(file_path, 'r') as f:
        map_file = json.load(f)

    GameState.entity_storage.reset()

    try:
        # validate map

        if not MAP_LOADER_VERSION == map_file["cmf_ver"]:
            raise ValueError(f"Map file version is imcompatible with the current version of Cue! (map file: {map_file['cmf_ver']}; supported: {MAP_LOADER_VERSION})")    

        for t in map_file["cmf_header"]["type_list"]:
            if not t in EntityTypeRegistry.entity_types:
                raise ValueError(f"Map file contains Cue entity types not supprted by the current app! (missing \"{t}\")")

        # load map data into Cue subsystems

        # GameState.asset_manager.preload(map_file["cmf_header"]["asset_list"])

        for e in map_file["cmf_data"]["map_entities"]:
            GameState.entity_storage.spawn(e["en_type"], e["en_name"], e["en_data"])

    except KeyError:
        raise ValueError("corrupted map file, missing json fields")

# == Map Compiler ==

# process param type prefixes for string-like types
def map_encode_entity_params(param):
    # if isinstance(param, str):
    #     return "str://" + param

    if isinstance(param, Vec2):
        return (param.x, param.y)

    elif isinstance(param, Vec3):
        return (param.x, param.y, param.z)

    raise TypeError("unsupported data type in entity data")

# saves a map file to disk from an `entity_export`, this function is really only used in the on-cue editor for map compilation
# *warn*: this func will not hesitate to override existing files!
def compile_map(file_path: str, entity_export: dict[str, tuple[str, dict]]):
    # collect all metadata for the `cmf_header`

    header_type_list = set()
    header_asset_list = set()

    for e in entity_export.values():
        header_type_list.add(e[0])
        
        # TODO: collect asset metadata

    # collect entity data for `cmf_data`

    entities = []

    for name, e in entity_export.items():
        params = copy.deepcopy(e[1]) # deepcopy to avoid modifying the source `entity_export`
        entities.append((name, e[0], e[1]))

    # dump the final json

    map_file = {
        "cmf_ver": MAP_LOADER_VERSION,
        "cmf_header": {
            "type_list": list(header_type_list),
            "asset_list": list(header_asset_list),
        },
        "cmf_data": {
            "map_entities": entities
        }
    }

    with open(file_path, 'w') as f:
        json.dump(map_file, f, indent=4, default=map_encode_entity_params)

