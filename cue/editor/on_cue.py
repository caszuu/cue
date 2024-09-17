import os, sys, time, pickle, json
from typing import Callable

import pygame as pg, pygame.math as pm
import numpy as np
import imgui

import filedialpy

from ..cue_state import GameState
from ..cue_sequence import CueSequencer
from ..cue_entity_storage import EntityStorage
from ..entities.cue_entity_types import EntityTypeRegistry

from ..rendering.cue_renderer import CueRenderer
from ..rendering.cue_camera import Camera
from ..rendering.cue_scene import RenderScene
from ..im2d.imgui_integ import CueImguiContext

from .. import cue_utils as utils
from ..rendering import cue_resources as res
from ..rendering import cue_batch as bat

from .. import cue_map as map
from .. import cue_sequence as seq

from ..components.cue_freecam import FreecamController

# == On-Cue Editor ==

# editors global state
class EditorState:
    # viewport state
        
    ui_ctx: CueImguiContext
    editor_freecam: FreecamController
    
    error_msg: str | None = None

    # ui state

    is_settings_win_open: bool = False
    is_perf_overlay_open: bool = False

    on_ensure_saved_success: Callable[[], None] | None = None

    # map state

    map_file_path: str | None = None
    has_unsaved_changes: bool = False

    # stores the maps entity datas; dict[en_name, tuple[en_data, tuple[en_type, en_data]]]
    entity_data_storage: dict[str, tuple[str, dict]]

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

def editor_error(msg: str) -> None:
    utils.error(msg)

    EditorState.error_msg = msg

# == editor map defs ==

def ensure_map_saved(on_success: Callable[[], None]) -> bool:
    if EditorState.has_unsaved_changes == False:
        on_success()
        return False

    imgui.open_popup("Unsaved Changes")
    EditorState.on_ensure_saved_success = on_success

    return True

from ..components.cue_transform import Transform

# init a default map to act as a background or as a new map
def editor_new_map():
    EditorState.map_file_path = None
    EditorState.has_unsaved_changes = False
    EditorState.entity_data_storage = {}
    
    reset_editor_ui()
    
    GameState.active_camera = Camera(GameState.renderer.win_aspect, 70)
    GameState.active_scene = RenderScene()
    GameState.entity_storage.reset()
    GameState.sequencer = CueSequencer(time.perf_counter()) # to del all scheduled seqs

    EditorState.editor_freecam = FreecamController(GameState.active_camera)

    pipeline = res.ShaderPipeline("cue/editor/test_trig.vert", "cue/editor/test_col.frag", "test_screenspace")
    mesh = res.GPUMesh(GameState.renderer.model_vao)
    mesh.write_to(np.array([0, 1, 0, 1, 1, 0, 1, 0, 0], dtype=np.dtypes.Float32DType), 3)

    trans = Transform(pm.Vector3(1, 0, 1), pm.Vector3(0, 0, 0), pm.Vector3(2, 2, 2))

    mesh_ins = bat.DrawBatch(res.GPUMesh(GameState.renderer.model_vao), pipeline, trans)
    mesh_ins.draw_count = 3

    GameState.active_scene.append(mesh_ins)

def editor_save_map(path: str | None) -> None:
    if path == None:
        path = filedialpy.saveFile(title="Save map file", filter=["*.json"])
        
        if not path: # cancel
            return

        EditorState.map_file_path = path
    
    utils.info(f"[editor] Compiling map file {path}..")

    # create entity exports

    entity_export_buf = {}

    for en_name, en in EditorState.entity_data_storage.items():
        en_type = GameState.entity_storage.entity_storage[en_name][1]

        entity_export_buf[en_name] = (en_name, en_type, en)

    # compile map file

    map.compile_map(path, entity_export_buf)

    EditorState.has_unsaved_changes = False

def editor_load_map() -> None:
    path = filedialpy.openFile(title="Open map file", filter=["*.json"])

    if not path: # cancel
        return

    utils.info(f"[editor] Loading map file {path}..")

    # clear the map data
    editor_new_map()

    # load up the map file

    try:
        with open(path, 'r') as f:
            map_file = json.load(f)
    except json.JSONDecodeError as e:
        editor_error("The file doesn't seem to be a map file or it's corrupted!")
        return
    except FileNotFoundError:
        editor_error("The map file not found!")
        return

    if map_file["cmf_ver"] != map.MAP_LOADER_VERSION:
        editor_error(f"The map file is saved with an unknown cmf format version! (cmf_ver: {map_file['cmf_ver']})")
        return

    for et in map_file["cmf_header"]["type_list"]:
        if not et in EntityTypeRegistry.entity_types:
            editor_error(f"The entity type \"{et}\" not found in the current app!")
            return

    # note: ignoring the compiled cmf_asset_files

    for map_en in map_file["cmf_data"]["map_entities"]:
        EditorState.entity_data_storage[map_en[0]] = (map_en[1], map.load_entity_data_params(map_en[2]))

# == ui defs ==

def perf_overlay():
    win_flags = imgui.WINDOW_NO_DECORATION | imgui.WINDOW_ALWAYS_AUTO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS | imgui.WINDOW_NO_FOCUS_ON_APPEARING | imgui.WINDOW_NO_NAV | imgui.WINDOW_NO_MOVE
    pad = 10

    viewport = imgui.get_main_viewport()
    imgui.set_next_window_position(viewport.work_pos.x + pad, viewport.work_pos.y + pad)
    imgui.set_next_window_bg_alpha(.35)

    with imgui.begin("Perf overlay", flags=win_flags):
        imgui.text("Performace overlay")
        imgui.separator()

        imgui.text(f"Frame time: {round(GameState.delta_time * 1000, 2)}ms")

        imgui.spacing(); imgui.spacing()

        imgui.text(f"Tick time: {round(GameState.cpu_tick_time * 1000, 2)}ms")
        imgui.text(f"Cpu Render Time: {round(GameState.cpu_render_time * 1000, 2)}ms")

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

            _, EditorState.is_perf_overlay_open = imgui.menu_item("Perf overlay", selected=EditorState.is_perf_overlay_open)

            imgui.end_menu()
        
        imgui.end_main_menu_bar()

    # workaround for imgui issue #331
    if unsaved_open:
        imgui.open_popup("Unsaved Changes")

    # == editor overlays ==

    if EditorState.is_perf_overlay_open:
        perf_overlay()

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
    
    if not EditorState.error_msg is None:
        imgui.open_popup("An Error")

    if imgui.begin_popup_modal("An Error", None, imgui.WINDOW_ALWAYS_AUTO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS)[0]:
        imgui.text(EditorState.error_msg)
        imgui.separator()

        if imgui.button("Ok"):
            EditorState.error_msg = None
            imgui.close_current_popup()

        imgui.end_popup()

def start_editor():
    print(f"\n[{utils.bold_escape}info{utils.reset_escape}] [bootstrap] starting the On-Cue Editor")

    # init engine

    t = time.perf_counter()
    GameState.sequencer = CueSequencer(t)
    GameState.entity_storage = EntityStorage()

    GameState.renderer = CueRenderer((1280, 720), vsync=True)
    pg.display.set_caption("On-Cue Editor")

    # init editor

    EditorState.ui_ctx = GameState.renderer.fullscreen_imgui_ctx

    editor_new_map()

    try:
        while True:
            # == event poll ==

            should_exit = False

            for e in pg.event.get():
                EditorState.ui_ctx.process_key_event(e)

                if e.type == pg.MOUSEMOTION:
                    EditorState.ui_ctx.set_mouse_input(e.pos)

                elif e.type == pg.VIDEORESIZE:
                    EditorState.ui_ctx.resize_display(e.size)
                    GameState.renderer.on_resize(e.size)
                    GameState.active_camera.re_aspect(GameState.renderer.win_aspect)

                elif e.type == pg.QUIT:
                    should_exit = True

                GameState.sequencer.send_event_id(e.type, e)
            
            EditorState.editor_freecam.set_capture(pg.mouse.get_pressed()[2])

            # == tick ==

            dt = time.perf_counter() - t
            t = time.perf_counter()

            GameState.delta_time = dt
            EditorState.ui_ctx.delta_time(dt)
            
            GameState.sequencer.tick(t)

            tt = time.perf_counter() - t

            # == frame ==

            EditorState.ui_ctx.set_as_current_context()
            imgui.new_frame()

            if should_exit:
                ensure_map_saved(lambda: sys.exit(0))

            editor_process_ui()

            GameState.renderer.frame(GameState.active_camera, GameState.active_scene)

            GameState.cpu_tick_time = tt # delayed by a frame to match cpu_render_time
            GameState.cpu_render_time = GameState.renderer.cpu_frame_time

    except Exception: # all-catch crash handler, just try to backup unsaved data before crashing
        exception_backup_save()
        raise