from . import cue_utils as utils

# a set of basic dev con commands

from . import cue_map
from .cue_state import GameState

def help_cmd(args: list[str]):
    utils.info("available commands:")

    for cmd in utils.cmd_callbacks.keys():
        utils.info(f" - {cmd}")

utils.add_dev_command("help", help_cmd)

def exit_cmd(args: list[str]):
    exit(0)

utils.add_dev_command("exit", exit_cmd)

def map_cmd(args: list[str]):
    if len(args) == 0:
        utils.error("no map specified, use 'map [map file path]' to load a cue map")
        return
    elif len(args) > 1:
        utils.error(f"unknown arguments; expected 1, got {len(args)}")
        return

    # try from asset dir
    try:
        cue_map.load_map(GameState.asset_manager.asset_dir + "/" + args[0])
        return
    except FileNotFoundError:
        pass

    # try as a full path
    try:
        cue_map.load_map(args[0])
        return
    except FileNotFoundError:
        pass

    utils.error("map file not found!")

utils.add_dev_command("map", map_cmd)

def assetc_flush(args: list[str]):
    GameState.asset_manager.reset()

utils.add_dev_command("flush_assetc", assetc_flush)