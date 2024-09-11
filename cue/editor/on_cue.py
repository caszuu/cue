import os, sys, time, pickle
from typing import Callable

import pygame as pg, pygame.math as pm
import numpy as np
import imgui

from ..cue_state import GameState
from ..cue_entity_storage import EntityStorage

from ..rendering.cue_renderer import CueRenderer
from ..rendering.cue_camera import Camera
from ..rendering.cue_scene import RenderScene
from ..im2d.imgui_integ import CueImguiContext

from .. import cue_utils as utils
from ..rendering import cue_resources as res
from ..rendering import cue_batch as bat

from .. import cue_map as map

# == On-Cue Editor ==

# editors global state
class EditorState:
    # viewport state
        
    ui_ctx: CueImguiContext
    renderer: CueRenderer

    pov_camera: Camera
    temp_scene: RenderScene

    # ui state

    is_settings_win_open: bool = False

    on_ensure_saved_success: Callable[[], None] | None = None

    # map state

    map_file_path: str | None = None
    has_unsaved_changes: bool = False

def reset_editor_ui():
    EditorState.is_settings_win_open = False
    EditorState.on_ensure_saved_success = None

# the last data dump before crashing, trying to lose minimal data here...
def exception_backup_save() -> None:
    # find a filename that doesn't exists

    path = "crash_backup_dump.pkl"

    i = 1
    while os.path.exists(path):
        path = f"crash_backup_dump_{i}.pkl"
        i += 1

    utils.error(f"Crash detected! Attempting to do a crash backup to {path}!")

    # dump map data before crashing

    dump_data = {}

    try: dump_data["editor_entity_data"] = EditorState.entity_data_storage
    except: pass

    try: dump_data["game_entity_data"] = GameState.entity_storage.entity_storage
    except: pass

    with open(path, 'wb') as f:
        pickle.dump(dump_data, f)

def ensure_map_saved(on_success: Callable[[], None]) -> bool:
    if EditorState.has_unsaved_changes == False:
        on_success()
        return False

    imgui.open_popup("Unsaved Changes")
    EditorState.on_ensure_saved_success = on_success

    return True

# init a default map to act as a background or as a new map
def editor_new_map():
    utils.info("Creating a new map..")

    EditorState.map_file_path = None
    EditorState.has_unsaved_changes = False
    
    reset_editor_ui()
    
    EditorState.pov_camera = Camera(EditorState.renderer.win_aspect)
    GameState.active_scene = RenderScene()
    GameState.entity_storage.reset()

    pipeline = res.ShaderPipeline("cue/editor/test_trig.vert", "cue/editor/menu.frag")
    mesh = res.GPUMesh(EditorState.renderer.model_vao)
    mesh.write_to(np.array([0, 1, 0, 1, 1, 0, 1, 0, 0], dtype=np.dtypes.Float32DType), 3)

    mesh_ins = bat.MeshBatch(None, res.GPUMesh(EditorState.renderer.model_vao), pipeline)
    mesh_ins.draw_count = 3

    GameState.active_scene.append(mesh_ins)

def editor_save_map(path: str | None) -> None:
    if path == None:
        raise NotImplementedError() # TODO: file dialog
    
    utils.info(f"[editor] Compiling map file {path}..")

    # create entity exports

    entity_export_buf = {}

    for en_name, en in EditorState.entity_data_storage.items():
        en_type = GameState.entity_storage[en_name][1]

        entity_export_buf[en_name] = (en_name, en_type, en)

    # compile map file

    map.compile_map(path, entity_export_buf)
    
# this is the `main` editor func where we dispatch work based on user's input
def editor_process_ui():
    EditorState.ui_ctx.set_as_current_context()

    # == main menu bar ==

    unsaved_open = False

    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File"):
            if imgui.menu_item("New map", None)[0]:
                unsaved_open = ensure_map_saved(lambda: editor_new_map())

            if imgui.menu_item("Open map", None)[0]:
                unsaved_open = ensure_map_saved(lambda: editor_load_map())

            if imgui.menu_item("Save map", "Ctrl+s")[0]:
                editor_save_map(EditorState.map_file_path)

            if imgui.menu_item("Save map as..")[0]:
                editor_save_map(None)

            imgui.separator()

            if imgui.menu_item("Test play", "Ctrl+t")[0]:
                pass

            if imgui.menu_item("Non-Test play")[0]:
                pass

            # imgui.separator()

            # clicked, EditorState.is_settings_win_open = imgui.menu_item("Map Settings", None, EditorState.is_settings_win_open)
            # if EditorState.is_settings_win_open:
            #     ui_map_settings()
            
            imgui.end_menu()

        if imgui.begin_menu("Tools"):
            if imgui.menu_item("Map tree")[0]:
                pass

            imgui.end_menu()
        
        imgui.end_main_menu_bar()

    # workaround for imgui issue #331
    if unsaved_open:
        imgui.open_popup("Unsaved Changes")

    # == popup modals ==

    if imgui.begin_popup_modal("Unsaved Changes", None, imgui.WINDOW_ALWAYS_AUTO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS)[0]:
        imgui.text("The current map has some unsaved changes which will be lost.\nDo you want to continue?")
        imgui.separator()

        if imgui.button("Ok"):
            EditorState.on_ensure_saved_success()
            imgui.close_current_popup()
            EditorState.on_ensure_saved_success = None

        imgui.same_line()

        if imgui.button("Cancel"):
            imgui.close_current_popup()
            EditorState.on_ensure_saved_success = None

        imgui.end_popup()

import math

def start_editor():
    print(f"\n[{utils.bold_escape}info{utils.reset_escape}] [bootstrap] starting the On-Cue Editor")

    # init window

    EditorState.renderer = CueRenderer((1280, 720), vsync=True)
    pg.display.set_caption("On-Cue Editor")

    EditorState.ui_ctx = EditorState.renderer.fullscreen_imgui_ctx
    t = time.perf_counter()

    GameState.entity_storage = EntityStorage()
    editor_new_map()

    try:
        while True:
            # == event poll ==

            for e in pg.event.get():
                EditorState.ui_ctx.process_key_event(e)

                if e.type == pg.MOUSEMOTION:
                    EditorState.ui_ctx.set_mouse_input(e.pos)

                elif e.type == pg.VIDEORESIZE:
                    EditorState.ui_ctx.resize_display(e.size)

                elif e.type == pg.QUIT:
                    sys.exit(0)

            # == tick ==

            dt = time.perf_counter() - t
            t = time.perf_counter()

            EditorState.ui_ctx.delta_time(dt)

            # == frame ==

            EditorState.ui_ctx.set_as_current_context()
            imgui.new_frame()

            editor_process_ui()

            EditorState.pov_camera.set_view(pm.Vector3(math.sin(t), 0., 0.), pm.Vector3(0., 0., 1.))
            EditorState.renderer.frame(EditorState.pov_camera, GameState.active_scene)

    except Exception: # all-catch crash handler, just try to backup unsaved data before crashing
        exception_backup_save()
        raise
