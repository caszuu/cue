import os, sys, time, pickle, json, traceback, copy
from typing import Callable, Any

import pygame as pg, pygame.math as pm
import numpy as np
import imgui

from pygame.math import Vector2 as Vec2, Vector3 as Vec3

import filedialpy

from ..cue_state import GameState
from ..cue_assets import AssetManager
from ..cue_sequence import CueSequencer
from ..cue_entity_storage import EntityStorage
from ..entities.cue_entity_types import EntityTypeRegistry, DevTickState

from ..components.cue_transform import Transform
from ..rendering.cue_renderer import CueRenderer
from ..rendering.cue_camera import Camera
from ..rendering.cue_scene import RenderScene
from ..im2d.imgui_integ import CueImguiContext

from .. import cue_utils as utils
from .. import cue_cmds
from ..rendering import cue_resources as res
from ..rendering import cue_batch as bat
from ..rendering import cue_gizmos as gizmo

from .. import cue_map as map
from .. import cue_sequence as seq

from ..components.cue_freecam import FreecamController

# == On-Cue Editor ==

EDITOR_ASSET_DIR = "assets/"
EDITOR_TEST_PLAY_CALLBACK = lambda map_path: utils.error("[editor] Test play callback not provided by launch script, can't Test play.")

# editors global state
class EditorState:
    # == viewport state ==
        
    ui_ctx: CueImguiContext
    editor_freecam: FreecamController
    
    error_msg: str | None = None

    # mode enum:
    #  0 - normal / none
    #  1 - move (key g)
    #  -1 - undo move
    #  2 - rotate (key r)
    #  -2 - undo rotate
    #  3 - scale (key f)
    #  -3 - undo scale
    edit_mode: int = 0

    # initial mouse position on edit mode change
    edit_mode_initial_mouse: tuple[int, int] | None = None

    # axis mode enum:
    #  0 - no axis / free
    #  1 - x axis
    #  2 - y axis
    #  3 - z axis
    edit_mode_axis: int = 0

    # == ui state ==

    is_settings_win_open: bool = False
    is_model_importer_open: bool = False
    is_entity_tree_open: bool = False
    is_asset_browser_open: bool = False
    is_collider_tool_open: bool = False

    is_perf_overlay_open: bool = False
    is_dev_con_open: bool = False

    on_ensure_saved_success: Callable[[], None] | None = None
    entity_tree_filter: str = ""

    drag_drop_payload_buffer: dict[int, Any] = {}
    next_payload_id: int = 0

    # == model import state ==

    assimp_scene: Any | None = None
    assimp_path: str | None = None

    assimp_sel_mesh: int = 0
    assimp_mesh_scale: np.ndarray = np.array([1., 1., 1.], dtype=np.float32)
    assimp_saved_msg: str | None = None

    # == tool states ==

    coll_tool_padding: Vec3 = Vec3()
    coll_tool_preview_enabled: bool = True
    coll_tool_coll_name: str = "new_entity_coll"
    coll_tool_wall_axis: int = 0
    coll_tool_subscene_id: str = ""
    
    coll_tool_mesh_cache: dict[str, np.ndarray] = {}

    # == map state ==

    map_file_path: str | None = None
    has_unsaved_changes: bool = False

    # == entity state ==

    # stores the maps entity datas; dict[en_name, tuple[en_type, en_data]]
    entity_data_storage: dict[str, tuple[str, dict]]

    # storage for entity type specific editor states
    dev_tick_storage: dict[str, Any]
    # stores dev tick error messages they may come up
    dev_tick_errors: dict[str, str]

    # currently editor-wide selected entity
    selected_entities: set[str] = set()
    focus_entity: str | None = None

    # entities currently with a editor panel open, don't have to be selected
    entities_in_editing: set[str] = set()
    # the editor panel (imgui window) ids map from entity names (persistent only for the current session; isn't saved)
    entity_editor_ids: dict[str, int] = {}
    next_editor_id: int = 0

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

# init a default map to act as a background or as a new map
def editor_new_map():
    EditorState.map_file_path = None
    EditorState.has_unsaved_changes = False
    EditorState.entity_data_storage = {}
    EditorState.dev_tick_storage = {}
    EditorState.dev_tick_errors = {}
    EditorState.selected_entities = set()
    EditorState.focus_entity = None
    EditorState.entities_in_editing = set()
    
    reset_editor_ui()
    
    GameState.entity_storage.reset()
    GameState.asset_manager.reset() # catch asset changes on map reloads
    GameState.sequencer = CueSequencer(time.perf_counter()) # to del all scheduled seqs
    GameState.active_scene = RenderScene()
    GameState.active_camera = Camera(GameState.renderer.win_aspect, 70)

    EditorState.editor_freecam = FreecamController(GameState.active_camera)

def editor_save_map(path: str | None = None) -> None:
    if path == None:
        path = filedialpy.saveFile(title="Save map file", filter=["*.json"])
        
        if not path: # cancel
            return

        EditorState.map_file_path = path
    
    utils.info(f"[editor] Compiling map file {path}..")

    # create entity exports

    entity_export_buf = {}

    for en_name, en in EditorState.entity_data_storage.items():
        entity_export_buf[en_name] = (en[0], en[1])

    # compile map file

    map.compile_map(path, entity_export_buf)

    EditorState.has_unsaved_changes = False

def editor_load_map(path: str | None = None) -> None:
    if path is None:
        path = filedialpy.openFile(title="Open map file", filter=["*.json"])

    if not path: # cancel
        return

    utils.info(f"[editor] Loading map file {path}..")

    # clear the map data
    editor_new_map()
    EditorState.map_file_path = path

    # load up the map file

    try:
        with open(path, 'r') as f:
            map_file = json.load(f)
    except json.JSONDecodeError:
        editor_error("The file doesn't seem to be a map file or it's corrupted!")
        return
    except FileNotFoundError:
        editor_error("The map file not found!")
        return

    if map_file["cmf_ver"] != map.MAP_LOADER_VERSION:
        editor_error(f"The map file is saved with an imcompatible cmf format version! (cmf_ver: {map_file['cmf_ver']}; expected: {map.MAP_LOADER_VERSION})")
        return

    for et in map_file["cmf_header"]["type_list"]:
        if not et in EntityTypeRegistry.entity_types:
            editor_error(f"The entity type \"{et}\" not found in the current app!")
            return

    # note: ignoring the compiled cmf_asset_files

    for map_en in map_file["cmf_data"]["map_entities"]:
        EditorState.entity_data_storage[map_en[0]] = (map_en[1], map.load_en_param_types(map_en[2]))

# override the engine's map loading to the editor stub
map.load_map = editor_load_map

# == editor entity defs ==

def handle_entity_rename(old_name: str, new_name: str) -> bool:
    # validate rename

    if not new_name: # no empty names
        return False

    if new_name in EditorState.entity_data_storage: # name conflict
        return False

    # handle renaming in all places where this entity might be refered to
    EditorState.entity_data_storage[new_name] = EditorState.entity_data_storage.pop(old_name)
    EditorState.entity_editor_ids[new_name] = EditorState.entity_editor_ids.pop(old_name)
    EditorState.dev_tick_storage.pop(old_name, None) # just discard it to be sure
    EditorState.dev_tick_errors.pop(old_name, None)

    EditorState.entities_in_editing.discard(old_name)
    EditorState.entities_in_editing.add(new_name)

    if old_name in EditorState.selected_entities:
        EditorState.selected_entities.discard(old_name)
        EditorState.selected_entities.add(new_name)
    
    return True

def add_new_prop(en_data: dict[str, Any], start_name: str, start_value: Any):
    if not start_name in en_data:
        en_data[start_name] = start_value
        return
    
    i = 1
    while True:
        start_name_extended = f"{start_name}_{i}"
        if not start_name_extended in en_data:
            en_data[start_name_extended] = start_value
            return
        
        i += 1

def props_editor_ui(props_id: str, props_to_edit: dict) -> bool:
    imgui.push_id(props_id)
    imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND, 0., 0., 0., 0.)

    imgui.spacing()

    changed_data = False
    with imgui.begin_table("Entity Properties", 2, imgui.TABLE_BORDERS | imgui.TABLE_RESIZABLE):
        imgui.table_next_row()
        imgui.table_next_column()
        imgui.text("prop")
        
        imgui.table_next_column()
        imgui.text("value")

        for prop, value in dict(props_to_edit).items():
            imgui.push_id(prop)

            # prop name
            imgui.table_next_row()
            imgui.table_next_column()
            imgui.push_item_width(-imgui.FLOAT_MIN)

            changed_name, new_prop = imgui.input_text("##prop", prop, flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
            if changed_name and not (new_prop in props_to_edit or not new_prop):
                    # new prop name, rename it
                    props_to_edit[new_prop] = props_to_edit.pop(prop)
                    imgui.pop_id()
                    imgui.push_id(new_prop)
                    prop = new_prop

            changed_data |= changed_name

            imgui.pop_item_width()

            # prop value
            imgui.table_next_column()
            imgui.push_item_width(-imgui.FLOAT_MIN)

            if isinstance(value, bool):
                imgui.pop_style_color()
                imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + imgui.get_content_region_available_width() * .5 - imgui.get_style().frame_padding[0] * 2.)

                changed_val, val = imgui.checkbox("##val", value)
                props_to_edit[prop] = val

                imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND, 0., 0., 0., 0.)
            elif isinstance(value, int | float):
                changed_val, val = imgui.drag_float("##val", value, .01)
                props_to_edit[prop] = val
            elif isinstance(value, Vec2):
                changed_val, val = imgui.drag_float2("##val", value.x, value.y, .01)
                props_to_edit[prop] = Vec2(val)
            elif isinstance(value, Vec3):
                changed_val, val = imgui.drag_float3("##val", value.x, value.y, value.z, .01)
                props_to_edit[prop] = Vec3(val)
            elif isinstance(value, str):
                changed_val, val = imgui.input_text("##val", value)
                props_to_edit[prop] = val
            # elif isinstance(value, list):
            elif isinstance(value, dict):
                imgui.pop_style_color()
                changed_val = props_editor_ui(prop, value)
                imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND, 0., 0., 0., 0.)
            else:
                imgui.text_disabled(repr(value))
                changed_val = False

            # prop drag n drop

            # with imgui.begin_drag_drop_source() as drag_drop_src:
            #         if drag_drop_src.dragging:
            #             # store into drag_drop buffer
            #             EditorState.drag_drop_payload_buffer[EditorState.next_payload_id] = props_to_edit[prop]
            # 
            #             imgui.set_drag_drop_payload("any_arbit", EditorState.next_payload_id.to_bytes(4, 'little'))
            #             imgui.text_disabled(repr(props_to_edit[prop]))
            # 
            #             EditorState.next_payload_id += 1

            with imgui.begin_drag_drop_target() as drag_drop_dst:
                if drag_drop_dst.hovered:
                    payload = imgui.accept_drag_drop_payload("any_arbit")
                    if payload is not None:
                        payload_id = int.from_bytes(payload, 'little')
                        props_to_edit[prop] = EditorState.drag_drop_payload_buffer.pop(payload_id)
                        changed_val = True

            changed_data |= changed_val

            imgui.pop_item_width()
            imgui.pop_id()

    imgui.pop_style_color()

    # add button

    if imgui.small_button("add prop"):
        imgui.open_popup("##add_prop")

    if imgui.is_item_hovered():
        imgui.begin_tooltip()
        imgui.text("Adds a new prop to entity props.")
        imgui.end_tooltip()

    # delete button

    imgui.same_line()
    if imgui.small_button("delete prop"):
        imgui.open_popup("##delete_prop")

    if imgui.is_item_hovered():
        imgui.begin_tooltip()
        imgui.text("Deletes a prop from entity props.")
        imgui.end_tooltip()
    
    # add menu

    if imgui.begin_popup("##add_prop"):
        imgui.text("Select prop type to add")
        imgui.separator()

        if imgui.selectable("Boolean")[0]:
            add_new_prop(props_to_edit, "new_bool", False)
            imgui.close_current_popup()

        if imgui.selectable("Number")[0]:
            add_new_prop(props_to_edit, "new_float", 0.)
            imgui.close_current_popup()

        if imgui.selectable("Vector 2")[0]:
            add_new_prop(props_to_edit, "new_vec2", Vec2())
            imgui.close_current_popup()

        if imgui.selectable("Vector 3")[0]:
            add_new_prop(props_to_edit, "new_vec3", Vec3())
            imgui.close_current_popup()

        if imgui.selectable("String / Path")[0]:
            add_new_prop(props_to_edit, "new_str", "")
            imgui.close_current_popup()

        if imgui.selectable("Sub-Properties")[0]:
            add_new_prop(props_to_edit, "new_props", {})
        
        imgui.end_popup()

    # delete menu
    
    if imgui.begin_popup("##delete_prop"):
        imgui.text("Select prop to delete")
        imgui.separator()

        for prop in props_to_edit.keys():
            if imgui.selectable(prop)[0]:
                props_to_edit.pop(prop)
                imgui.close_current_popup()
                break
        
        imgui.end_popup()

    imgui.spacing()
    imgui.pop_id()
    return changed_data

def entity_edit_ui(en_name: str):
    edit_id = EditorState.entity_editor_ids.setdefault(en_name, EditorState.next_editor_id)
    if edit_id == EditorState.next_editor_id:
        EditorState.next_editor_id += 1

    imgui.set_next_window_size(500, 350, imgui.FIRST_USE_EVER)

    expanded, opened = imgui.begin(f"Entity Editor - {en_name}###entity_edit_{edit_id}", closable=True, flags=imgui.WINDOW_NO_SAVED_SETTINGS)
    if opened:
        if not expanded:
            imgui.end()
            return # unless we return here, imgui crashes

        if EditorState.focus_entity is not None and EditorState.focus_entity == en_name:
            imgui.set_window_focus()
            EditorState.focus_entity = None

        # entity header

        en_type, en_data = EditorState.entity_data_storage[en_name]

        imgui.push_item_width(imgui.get_content_region_available()[0] * .3)
        changed_name, new_en_name = imgui.input_text("entity name", en_name); imgui.same_line()
        changed_type, new_en_type_id = imgui.combo("entity type", EntityTypeRegistry.entity_names.index(en_type), EntityTypeRegistry.entity_names)
        imgui.pop_item_width()

        if changed_name:
            if handle_entity_rename(en_name, new_en_name):
                EditorState.has_unsaved_changes = True
                en_name = new_en_name

        if changed_type:
            # handle cleanup and change of the entity type
            new_en_type = EntityTypeRegistry.entity_names[new_en_type_id]
            en_data = EntityTypeRegistry.entity_types[new_en_type].default_data()

            EditorState.entity_data_storage[en_name] = (new_en_type, en_data)
            EditorState.dev_tick_storage.pop(en_name, None) # discard probably uncompatable editor state
            EditorState.dev_tick_errors.pop(en_name, None)

            EditorState.has_unsaved_changes = True
            en_type = new_en_type

        imgui.separator()

        # entity props

        imgui.text("entity props:")
        imgui.indent()

        changed_data = props_editor_ui("__entity_data", en_data)
        imgui.spacing()
        imgui.unindent()

        dev_error = EditorState.dev_tick_errors.get(en_name, None)
        if dev_error is not None:
            imgui.text("entity status:")
            imgui.same_line()
            with imgui.begin_child("dev_tick_report", border=True):
                imgui.push_style_color(imgui.COLOR_TEXT, 1., .35, .35, 1.)
                imgui.text_wrapped(dev_error)
                imgui.pop_style_color()
        else:
            imgui.text("entity status: no entity errors.")

        if changed_data:
            EditorState.dev_tick_storage.pop(en_name, None) # delete previos state to reload entity with changes
            EditorState.dev_tick_errors.pop(en_name, None)
            EditorState.has_unsaved_changes = True

    else:
        # editor panel closed
        EditorState.entities_in_editing.discard(en_name)

    imgui.end()

def get_new_entity_name(initial_name: str = "new_entity") -> str:
    en_name = initial_name
    
    if en_name in EditorState.entity_data_storage:
        stripped_name = initial_name.strip("0123456789")
        
        if stripped_name.endswith("_"):
            stripped_name = stripped_name[:-1]
        else:
            stripped_name = initial_name

        i = 0
        while True:
            en_name = f"{stripped_name}_{i}"
            if not en_name in EditorState.entity_data_storage:
                break

            i += 1
    
    return en_name

def editor_create_entity():
    new_en = ("bt_static_mesh", EntityTypeRegistry.entity_types["bt_static_mesh"].default_data())
    en_name = get_new_entity_name()

    EditorState.has_unsaved_changes = True

    EditorState.entity_data_storage[en_name] = new_en
    EditorState.selected_entities = {en_name}

    # immidatelly open an editor for the entity
    EditorState.entities_in_editing.add(en_name)

def editor_duplicate_entity():
    if not EditorState.selected_entities:
        return

    new_sel = set()

    for en in EditorState.selected_entities:
        orig_en = EditorState.entity_data_storage[en]

        new_en = (orig_en[0], copy.deepcopy(orig_en[1]))
        en_name = get_new_entity_name(en)

        EditorState.entity_data_storage[en_name] = new_en
        new_sel.add(en_name)

        # immidatelly open an editor for the entity
        EditorState.entities_in_editing.add(en_name)

    EditorState.selected_entities = new_sel
    EditorState.has_unsaved_changes = True

def editor_delete_entity(next_to_select: str | None = None):
    if not EditorState.selected_entities:
        return

    EditorState.has_unsaved_changes = True

    for en in EditorState.selected_entities:
        EditorState.entity_data_storage.pop(en)
        
        EditorState.entities_in_editing.discard(en) # close the entities editing panel if was open
        EditorState.dev_tick_storage.pop(en, None) # cleanup dev state (if any) to save memory
    
    if next_to_select is not None:
        EditorState.selected_entities = {next_to_select}
    else:
        EditorState.selected_entities = set()

def entity_tree_ui():
    imgui.set_next_window_size(305, 350, condition=imgui.FIRST_USE_EVER)

    with imgui.begin("Entity Tree", None):
        add_en = imgui.button("+")
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text("Create an entity"); imgui.same_line()
            # imgui.text_colored("(Ctrl+a)", .5, .5, .5, 1.)
            imgui.end_tooltip()

        imgui.same_line()
        
        del_en = imgui.button("-")
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text("Delete an entity"); imgui.same_line()
            # imgui.text_colored("(Ctrl+Del)", .5, .5, .5, 1.)
            imgui.end_tooltip()

        imgui.same_line()

        dup_en = imgui.button("d")
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text("Duplicate an entity"); imgui.same_line()
            # imgui.text_colored("(Ctrl+d)", .5, .5, .5, 1.)
            imgui.end_tooltip()

        imgui.same_line()

        imgui.push_item_width(imgui.get_content_region_available()[0] * .8)
        _, EditorState.entity_tree_filter = imgui.input_text("filter", value=EditorState.entity_tree_filter)
        filter_state = EditorState.entity_tree_filter
        imgui.pop_item_width()

        next_in_filter: str | None = None
        last_was_selected: bool = False

        if imgui.begin_child("entity_tree_list", 0, 0, True):
            for name, en in EditorState.entity_data_storage.items():
                if filter_state not in name:
                    continue

                has_error = EditorState.dev_tick_errors.get(name, None) is not None
                if has_error:
                    imgui.push_style_color(imgui.COLOR_TEXT, 1., .35, .35, 1.)

                clicked, selected = imgui.selectable(name, selected=name in EditorState.selected_entities)
                if clicked:
                    EditorState.focus_entity = name

                    if pg.key.get_mods() & pg.KMOD_SHIFT:
                        EditorState.selected_entities.add(name)
                    else:
                        EditorState.selected_entities = {name}
                
                if has_error:
                    imgui.pop_style_color()

                # open entities editor on double click
                if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(imgui.MOUSE_BUTTON_LEFT):
                    EditorState.entities_in_editing.add(name)

                # check for getting next selection in order
                if selected:
                    last_was_selected = True
                elif last_was_selected:
                    last_was_selected = False
                    next_in_filter = name

                imgui.same_line()
                imgui.text_colored(f"({en[0]})", .5, .5, .5, 1.)
            
            imgui.end_child()
        
        if add_en:
            editor_create_entity()
        
        if del_en:
            editor_delete_entity(next_in_filter)

        if dup_en:
            editor_duplicate_entity()

# == editor asset importer ==

try:
    import pyassimp as assimp
    assimp_supported = True
except:
    utils.warn("Failed to import assimp, Model Importer will not work!")
    assimp_supported = False

def model_import_ui() -> None:
    with imgui.begin("Model Importer", None):
        if not assimp_supported:
            imgui.text("Failed to import Assimp, make sure Assimp is properly\ninstalled before using the Model Importer!")
            return

        if imgui.button("Import External Model"):
            # import a model file using assimp

            EditorState.assimp_path = filedialpy.openFile(title="Open a model file")
            
            if not EditorState.assimp_path:
                return

            try:
                # try load the model scene
                with assimp.load(EditorState.assimp_path, None, processing=assimp.postprocess.aiProcess_Triangulate) as scene:
                    utils.info(f"[editor] Imported an external model file: {EditorState.assimp_path}")
                    EditorState.assimp_scene = scene

            except assimp.AssimpError as e:
                utils.error(f"Failed to load a model file {EditorState.assimp_path}: {e}")
                EditorState.assimp_scene = None
            except ValueError as e:
                utils.error(f"Failed to load a model file {EditorState.assimp_path}: {e}")
                EditorState.assimp_scene = None
            
            except: # all-catch to prevent editor crash
                utils.error(f"Failed to load a model file {EditorState.assimp_path}")
                EditorState.assimp_scene = None

            EditorState.assimp_saved_msg = None
            EditorState.assimp_sel_mesh = 0
            EditorState.assimp_mesh_scale = np.array([1., 1., 1.], dtype=np.float32)
            
        imgui.same_line()
        imgui.text(f"Model File: {None if EditorState.assimp_path is None else os.path.basename(EditorState.assimp_path)}")
        
        imgui.separator()

        with imgui.begin_tab_bar("Model Importer Tab Bar"):
            if imgui.begin_tab_item("Mesh Data")[0]:
                # mesh importer

                if EditorState.assimp_scene is not None:
                    reload_model, EditorState.assimp_sel_mesh = imgui.combo("selected mesh", EditorState.assimp_sel_mesh, [str(m) for m in EditorState.assimp_scene.meshes])
                    reload_scale, scale = imgui.drag_float3("mesh scale", *EditorState.assimp_mesh_scale)
                    if reload_scale:
                        EditorState.assimp_mesh_scale = np.array(scale, dtype=np.float32)

                    imgui.spacing(); imgui.spacing()

                    imgui.text(f"Mesh vertex count: {len(EditorState.assimp_scene.meshes[EditorState.assimp_sel_mesh].vertices)}")
                    imgui.text(f"Mesh index count: {len(EditorState.assimp_scene.meshes[EditorState.assimp_sel_mesh].faces) * 3}")
                else:
                    reload_model, EditorState.assimp_sel_mesh = imgui.combo("selected mesh", 0, [])
                    reload_scale, scale = imgui.drag_float3("mesh scale", *EditorState.assimp_mesh_scale)
                    if reload_scale:
                        EditorState.assimp_mesh_scale = np.array(scale, dtype=np.float32)

                    imgui.spacing(); imgui.spacing()

                    imgui.text(f"Mesh vertex count: No mesh")
                    imgui.text(f"Mesh index count: No mesh")

                if reload_model:
                    EditorState.assimp_saved_msg = None
                    EditorState.assimp_mesh_scale = np.array([1., 1., 1.], dtype=np.float32)

                imgui.spacing(); imgui.spacing()

                if imgui.button("Save as a Cue Mesh") and not EditorState.assimp_path is None and not EditorState.assimp_scene is None:
                    save_path = filedialpy.saveFile(os.path.splitext(os.path.basename(EditorState.assimp_path))[0])
                    
                    mesh = EditorState.assimp_scene.meshes[EditorState.assimp_sel_mesh]
                    vert_count = len(mesh.vertices)
                    face_count = len(mesh.faces)

                    if not save_path:
                        imgui.end_tab_item()
                        return

                    vert_buf = np.empty((3 * vert_count,), dtype=np.float32)
                    norm_buf = np.empty((3 * vert_count,), dtype=np.float32)
                    uv_buf = np.empty((2 * vert_count,), dtype=np.float32)

                    elem_buf = np.empty((3 * face_count,), dtype=np.uint32)

                    # fill vert_buf

                    if not mesh.normals.any():
                        raise ValueError("No mesh normal components!")

                    if not mesh.texturecoords.any():
                        raise ValueError("No UV components!")

                    vert_buf[:] = (mesh.vertices * EditorState.assimp_mesh_scale).flatten()
                    norm_buf[:] = mesh.normals.flatten()

                    for vi in range(vert_count):
                        uv_buf[vi * 2:vi * 2 + 2] = mesh.texturecoords[0][vi][:2] # only using the first uv coords array, assuming this is correct?

                    # fill elem_buf
                    elem_buf[:] = mesh.faces.flatten()

                    # export to a game ready numpy archive
                    np.savez(save_path, vert_data=vert_buf, norm_data=norm_buf, uv_data=uv_buf, elem_data=elem_buf)

                    utils.info(f"[editor] Saved a new mesh file to {save_path}!")
                    EditorState.assimp_saved_msg = f"Saved to {os.path.basename(save_path)}!"
                
                if EditorState.assimp_saved_msg is not None:
                    imgui.same_line()
                    imgui.text(EditorState.assimp_saved_msg)

                imgui.end_tab_item()

# == specific editor tool ui ==

# currently only supports any entity with standard ModelRenderer and Transform entity data params, assuming Transform is world space
def compute_model_bounds(en_data: dict) -> tuple[Vec3, Vec3]:
    # fetch relevant data from model entity
    test_trans = Transform(en_data["t_pos"], en_data["t_rot"], en_data["t_scale"])
    
    vert_data = EditorState.coll_tool_mesh_cache.get(en_data["a_model_mesh"], None)
    if vert_data is None:
        with np.load(os.path.join(GameState.asset_manager.asset_dir, en_data["a_model_mesh"])) as mesh_data:
            vert_data = mesh_data["vert_data"]
            EditorState.coll_tool_mesh_cache[en_data["a_model_mesh"]] = vert_data

    vert_count = vert_data.shape[0] // 3
    axis_bins = np.zeros((3, vert_count))

    # transform the vertex data
    for i in range(vert_count):
        world_vert = test_trans._trans_matrix @ np.array((*vert_data[i * 3: i * 3 + 3], 1.), dtype=np.float32)

        axis_bins[0,i] = world_vert[0]
        axis_bins[1,i] = world_vert[1]
        axis_bins[2,i] = world_vert[2]

    # minmax transformed data
    min_p = Vec3(np.min(axis_bins[0]), np.min(axis_bins[1]), np.min(axis_bins[2]))
    max_p = Vec3(np.max(axis_bins[0]), np.max(axis_bins[1]), np.max(axis_bins[2]))

    return (min_p, max_p)

def collider_tool_ui():
    with imgui.begin("Collider Tool"):
        _, tool_mode = imgui.combo("tool mode", 0, ["AABBs"])

        # none or invalid selected
        # box scale or padding

        imgui.separator()

        if tool_mode == 0: # AABB wrapping mode
            selected_count = len(EditorState.selected_entities)

            for en in EditorState.selected_entities:
                t = EditorState.entity_data_storage[en][0]

                if t != "bt_static_mesh":
                    selected_count = -1
                    break

            if EditorState.focus_entity is not None:
                EditorState.coll_tool_coll_name = EditorState.focus_entity
                
                stripped_name = EditorState.coll_tool_coll_name.strip("0123456789")
                if stripped_name.endswith("_"):
                    EditorState.coll_tool_coll_name = stripped_name[:-1]

                EditorState.coll_tool_coll_name += "_coll"

            _, padding = imgui.drag_float3("aabb padding", *EditorState.coll_tool_padding, change_speed=.01)
            EditorState.coll_tool_padding = Vec3(padding)

            _, EditorState.coll_tool_wall_axis = imgui.combo("wall mode", EditorState.coll_tool_wall_axis, ["none", "+x", "+y", "+z", "-x", "-y", "-z"])
            _, EditorState.coll_tool_subscene_id = imgui.input_text("subscene id", EditorState.coll_tool_subscene_id); imgui.same_line()
            imgui.text_disabled("(?)")

            if imgui.is_item_hovered():
                imgui.set_tooltip("Phys subscenes are a manual optimalization for grouping spacially adjacent colliders.\nit allows high collider detail areas to not affect performace when not near the test ray.\n\nuse any string as the subscene id and separate by dots for multi-level subscenes\n(eg. `r1`, `r1.f2`, `r1.stairs.top`; `` for top-level scene / don't use subscenes)")

            imgui.spacing(); imgui.spacing()

            # calc AABB
            if selected_count > 0:
                min_p = Vec3(float('inf'), float('inf'), float('inf'))
                max_p = Vec3(-float('inf'), -float('inf'), -float('inf'))

                try:
                    for en in EditorState.selected_entities:
                        box = compute_model_bounds(EditorState.entity_data_storage[en][1])

                        min_p.x = min(min_p.x, box[0].x)
                        min_p.y = min(min_p.y, box[0].y)
                        min_p.z = min(min_p.z, box[0].z)

                        max_p.x = max(max_p.x, box[1].x)
                        max_p.y = max(max_p.y, box[1].y)
                        max_p.z = max(max_p.z, box[1].z)
                
                except:
                    selected_count = -2

                min_p -= EditorState.coll_tool_padding / 2
                max_p += EditorState.coll_tool_padding / 2

                # wall mode

                if EditorState.coll_tool_wall_axis > 0:
                    axis_index = (EditorState.coll_tool_wall_axis - 1) % 3

                    wall_edge_coord = (min_p[axis_index] + max_p[axis_index]) / 2
                    wall_thickness = .05

                    if (EditorState.coll_tool_wall_axis - 1) < 3: # if positive dir:
                        max_p[axis_index] = wall_edge_coord
                        min_p[axis_index] = wall_edge_coord - wall_thickness
                    else: # else negative dir:
                        max_p[axis_index] = wall_edge_coord + wall_thickness
                        min_p[axis_index] = wall_edge_coord

            # preview and export

            if selected_count <= 0:
                imgui.push_style_var(imgui.STYLE_ALPHA, .5)

            create_coll = imgui.button("add aabb"); imgui.same_line(spacing=8.)
            _, preview = imgui.checkbox("preview", EditorState.coll_tool_preview_enabled)

            if selected_count <= 0:
                imgui.pop_style_var()

                imgui.push_style_color(imgui.COLOR_TEXT, 1., .35, .35)
                imgui.same_line()
                
                if selected_count == -2:
                    imgui.text("error while calculating bounds."); imgui.same_line()
                    imgui.text_disabled("(?)"); imgui.pop_style_color()

                    if imgui.is_item_hovered():
                        imgui.set_tooltip("a python exception was raised during boundary calculation.\nmake sure all selected entities are without errors.")
                elif selected_count == -1:
                    imgui.text("invalid entities selected."); imgui.same_line()
                    imgui.text_disabled("(?)"); imgui.pop_style_color()

                    if imgui.is_item_hovered():
                        imgui.set_tooltip("some selected entities (any that are not bt_static_mesh)\ncan't be used for boundary calculations.")
                elif selected_count == 0:
                    imgui.text("no entities selected."); imgui.same_line()
                    imgui.text_disabled("(?)"); imgui.pop_style_color()

                    if imgui.is_item_hovered():
                        imgui.set_tooltip("to auto-create an AABB, one or more entities (of type bt_static_mesh) must be selected\nas the wanted elements and guideline to be covered by the AABB.")

            else:
                EditorState.coll_tool_preview_enabled = preview

                if EditorState.coll_tool_preview_enabled:
                    gizmo.draw_box(min_p, max_p, Vec3(.35, 1., .9))
    
                if create_coll:
                    imgui.open_popup("create_coll_popup")
                
                with imgui.begin_popup("create_coll_popup") as create_popup:
                    if create_popup.opened:
                        entered, EditorState.coll_tool_coll_name = imgui.input_text("new entity name", EditorState.coll_tool_coll_name, flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
                        imgui.text_disabled("enter to confirm, click outside to cancel")

                        if entered:
                            coll_data = {
                                "t_pos": (min_p + max_p) / 2,
                                "t_scale": max_p - min_p,
                                "phys_subscene_id": EditorState.coll_tool_subscene_id,
                            }

                            new_en = ("bt_phys_aabb", coll_data)
                            en_name = get_new_entity_name(EditorState.coll_tool_coll_name)

                            EditorState.has_unsaved_changes = True

                            EditorState.entity_data_storage[en_name] = new_en
                            EditorState.selected_entities = {en_name}

                            # immidatelly open an editor for the entity
                            EditorState.entities_in_editing.add(en_name)

                            imgui.close_current_popup()

# == ui defs ==

asset_preview_tex = None

def asset_browser_item(name: str, path: str):
    imgui.bullet(); imgui.same_line()
    imgui.selectable(name)

    # drag n drop source

    with imgui.begin_drag_drop_source() as drag_drop_src:
        if drag_drop_src.dragging:
            # store into drag_drop buffer
            EditorState.drag_drop_payload_buffer[EditorState.next_payload_id] = path

            imgui.set_drag_drop_payload("any_arbit", EditorState.next_payload_id.to_bytes(4, 'little'))
            imgui.text_disabled(path)

            EditorState.next_payload_id += 1

    # tooltip preview

    if imgui.is_item_hovered():
        filename, fileext = os.path.splitext(name)

        if fileext in image_formats:
            with imgui.begin_tooltip():
                global asset_preview_tex
                asset_preview_tex = GameState.asset_manager.load_texture(EDITOR_ASSET_DIR + "/" + path)

                imgui.image(asset_preview_tex.texture_handle, 256 * (asset_preview_tex.texture_size[0] / asset_preview_tex.texture_size[1]), 256)

def recurse_asset_subdir(dirpath: str, dirname: str):
    imgui.push_id(dirpath)
    if imgui.tree_node(dirname):
        for name in os.listdir(dirpath):
            if os.path.isfile(dirpath + "/" + name):
                asset_browser_item(name, (dirpath + "/" + name).removeprefix(EDITOR_ASSET_DIR + "/"))
            else:
                recurse_asset_subdir(dirpath + "/" + name, name + "/")

        imgui.tree_pop()

    imgui.pop_id()

image_formats = [".jpg", ".png", ".webp", ".bmp", ".tiff", ".gif"]

def asset_browser_ui():
    with imgui.begin("Asset Browser"):
        if not os.path.exists(EDITOR_ASSET_DIR):
            imgui.text_disabled(f"Asset path \"{EDITOR_ASSET_DIR}\" doesn't exists")
            return

        for name in os.listdir(EDITOR_ASSET_DIR):
            if os.path.isfile(EDITOR_ASSET_DIR + "/" + name):
                asset_browser_item(name, name)
            else:
                recurse_asset_subdir(EDITOR_ASSET_DIR + "/" + name, name + "/")

# this is the `main` editor func where we dispatch work based on user's input
def editor_process_ui():
    EditorState.ui_ctx.set_as_current_context()

    # == main menu bar ==

    unsaved_open = False

    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File"):
            if imgui.menu_item("New map", None)[0]:
                unsaved_open = ensure_map_saved(lambda: editor_new_map())

            if imgui.menu_item("Open map")[0]:
                unsaved_open = ensure_map_saved(lambda: editor_load_map())

            if imgui.menu_item("Save map", "Ctrl+s")[0]:
                editor_save_map(EditorState.map_file_path)

            if imgui.menu_item("Save map as..")[0]:
                editor_save_map()

            imgui.separator()

            if imgui.menu_item("Test play", "Ctrl+t")[0] and EditorState.map_file_path:
                EDITOR_TEST_PLAY_CALLBACK(EditorState.map_file_path)

            # imgui.separator()

            # clicked, EditorState.is_settings_win_open = imgui.menu_item("Map Settings", None, EditorState.is_settings_win_open)
            # if EditorState.is_settings_win_open:
            #     ui_map_settings()
            
            imgui.end_menu()

        if imgui.begin_menu("Tools"):
            _, EditorState.is_entity_tree_open = imgui.menu_item("Entity Tree", selected=EditorState.is_entity_tree_open)
            _, EditorState.is_asset_browser_open = imgui.menu_item("Asset Browser", selected=EditorState.is_asset_browser_open)

            imgui.separator()

            _, EditorState.is_collider_tool_open = imgui.menu_item("Collider Tool", selected=EditorState.is_collider_tool_open)
            _, EditorState.is_model_importer_open = imgui.menu_item("Model Importer", selected=EditorState.is_model_importer_open)
            _, EditorState.is_dev_con_open = imgui.menu_item("Developer Console", selected=EditorState.is_dev_con_open)

            imgui.separator()

            _, EditorState.is_perf_overlay_open = imgui.menu_item("Perf overlay", selected=EditorState.is_perf_overlay_open)

            imgui.end_menu()
        
        imgui.end_main_menu_bar()

    # workaround for imgui issue #331
    if unsaved_open:
        imgui.open_popup("Unsaved Changes")

    # == editor windows and overlays ==
    
    if EditorState.is_entity_tree_open:
        entity_tree_ui()

    if EditorState.is_model_importer_open:
        model_import_ui()

    if EditorState.is_asset_browser_open:
        asset_browser_ui()

    if EditorState.is_collider_tool_open:
        collider_tool_ui()

    for en in list(EditorState.entities_in_editing): # note: doing a copy here, as [entities_in_editing] might change mid iteration 
        entity_edit_ui(en)

    if EditorState.is_dev_con_open:
        EditorState.is_dev_con_open = utils.show_developer_console()

    if EditorState.is_perf_overlay_open:
        utils.show_perf_overlay()

    if EditorState.edit_mode > 0:
        with utils.begin_dev_overlay("edit_mode_info", 1):
            imgui.text("Editing Mode")
            imgui.separator()

            if EditorState.edit_mode == 1:
                imgui.text("mode: move")
            elif EditorState.edit_mode == 2:
                imgui.text("mode: rotate")
            elif EditorState.edit_mode == 3:
                imgui.text("mode: scale")

            if EditorState.edit_mode_axis == 0:
                imgui.text("axis: free")
            elif EditorState.edit_mode_axis == 1:
                imgui.text("axis: X")
            elif EditorState.edit_mode_axis == 2:
                imgui.text("axis: Y")
            elif EditorState.edit_mode_axis == 3:
                imgui.text("axis: Z")

            imgui.spacing(); imgui.spacing()

            imgui.push_style_color(imgui.COLOR_TEXT, .6, .6, .6, 1.)
            imgui.text("left-click to apply\nescape to cancel")
            imgui.pop_style_color()

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

def edit_mode_capture_keybinds(e) -> bool:
    if imgui.is_any_item_active() or not EditorState.selected_entities:
        change = EditorState.edit_mode > 0

        EditorState.edit_mode = -EditorState.edit_mode if EditorState.edit_mode > 0 else EditorState.edit_mode
        EditorState.edit_mode_initial_mouse = None
        EditorState.edit_mode_axis = 0

        return change

    if e.type == pg.KEYDOWN and e.dict['key'] == pg.K_ESCAPE:
        EditorState.edit_mode = -EditorState.edit_mode
        EditorState.edit_mode_initial_mouse = None
        EditorState.edit_mode_axis = 0
        return True
    elif (e.type == pg.KEYDOWN and e.dict['key'] == pg.K_RETURN) or (e.type == pg.MOUSEBUTTONDOWN and e.dict['button'] == 1):
        EditorState.edit_mode = 0
        EditorState.edit_mode_initial_mouse = None
        EditorState.edit_mode_axis = 0
        return True
    
    elif e.type == pg.KEYDOWN and e.dict['key'] == pg.K_g:
        EditorState.edit_mode = 1
        EditorState.edit_mode_initial_mouse = pg.mouse.get_pos()
        return True
    elif e.type == pg.KEYDOWN and e.dict['key'] == pg.K_r:
        EditorState.edit_mode = 2
        EditorState.edit_mode_initial_mouse = pg.mouse.get_pos()
        return True
    elif e.type == pg.KEYDOWN and e.dict['key'] == pg.K_f:
        EditorState.edit_mode = 3
        EditorState.edit_mode_initial_mouse = pg.mouse.get_pos()
        return True

    elif e.type == pg.KEYDOWN and e.dict['key'] == pg.K_x:
        EditorState.edit_mode_axis = 1
    elif e.type == pg.KEYDOWN and e.dict['key'] == pg.K_y:
        EditorState.edit_mode_axis = 2
    elif e.type == pg.KEYDOWN and e.dict['key'] == pg.K_z:
        EditorState.edit_mode_axis = 3

    return False

def editor_wide_keybinds(e):
    if e.type != pg.KEYDOWN:
        return

    elif e.dict['key'] == pg.K_s and e.dict['mod'] & pg.KMOD_CTRL:
        editor_save_map(EditorState.map_file_path)

    elif e.dict['key'] == pg.K_t and e.dict['mod'] & pg.KMOD_CTRL :
        if EditorState.map_file_path:
            EDITOR_TEST_PLAY_CALLBACK(EditorState.map_file_path)
        else:    
            utils.warn("[editor] Test mode cannot be used before the map is saved to disk, please save map first")

def editor_freecam_speed_tick():
    if pg.key.get_mods() & pg.KMOD_SHIFT:
        FreecamController.free_accel = 60
    else:
        FreecamController.free_accel = 30

    GameState.static_sequencer.next(editor_freecam_speed_tick)

def start_editor():
    print(f"\n[{utils.bold_escape}info{utils.reset_escape}] [bootstrap] starting the On-Cue Editor")

    # init engine

    GameState.current_time = time.perf_counter()
    GameState.static_sequencer = CueSequencer(GameState.current_time)
    GameState.entity_storage = EntityStorage()
    GameState.asset_manager = AssetManager(EDITOR_ASSET_DIR)

    GameState.renderer = CueRenderer((1280, 720), vsync=True)
    pg.display.set_caption("On-Cue Editor")

    # init editor

    EditorState.ui_ctx = GameState.renderer.fullscreen_imgui_ctx

    editor_new_map()
    editor_freecam_speed_tick()

    try:
        while True:
            # == event poll ==

            should_exit = False
            edit_mode_changed = False

            EditorState.ui_ctx.set_as_current_context()

            for e in pg.event.get():
                EditorState.ui_ctx.process_key_event(e)
                
                if e.type == pg.MOUSEMOTION:
                    EditorState.ui_ctx.set_mouse_input(e.pos)

                elif e.type == pg.QUIT:
                    should_exit = True

                # capture edit mode keybinds
                edit_mode_changed |= edit_mode_capture_keybinds(e)

                editor_wide_keybinds(e)

                GameState.sequencer.send_event_id(e.type, e)
                GameState.static_sequencer.send_event_id(e.type, e)
            
            EditorState.editor_freecam.set_capture(pg.mouse.get_pressed()[2])

            if hasattr(GameState, "next_map_deferred"):
                map.load_map(GameState.next_map_deferred)

            # == tick ==

            dt = time.perf_counter() - GameState.current_time
            GameState.current_time = time.perf_counter()

            imgui.new_frame()

            GameState.delta_time = dt
            EditorState.ui_ctx.delta_time(dt)
            
            GameState.sequencer.tick(GameState.current_time)
            GameState.static_sequencer.tick(GameState.current_time)

            if should_exit:
                ensure_map_saved(lambda: sys.exit(0))
            editor_process_ui()

            # perform dev/editor ticks

            dev_state = DevTickState(
                edit_mode=EditorState.edit_mode,
                edit_mode_axis=EditorState.edit_mode_axis,
                edit_mode_changed=edit_mode_changed,
                edit_mode_mouse_diff=(pg.mouse.get_pos()[0] - EditorState.edit_mode_initial_mouse[0], -(pg.mouse.get_pos()[1] - EditorState.edit_mode_initial_mouse[1])) if EditorState.edit_mode_initial_mouse is not None else None,

                is_entity_selected=False, # will be set per entity
                suggested_initial_pos=EditorState.editor_freecam.free_pos + (EditorState.editor_freecam.free_forward * 2.),

                view_pos=EditorState.editor_freecam.free_pos,
                view_forward=EditorState.editor_freecam.free_forward,
                view_right=EditorState.editor_freecam.free_right_flat,
                view_up=EditorState.editor_freecam.free_up,
            )

            if EditorState.edit_mode:
                EditorState.has_unsaved_changes = True

            for name, en in EditorState.entity_data_storage.items():
                if name in EditorState.dev_tick_errors:
                    continue # do not waste time ticking erroneous entities
                
                entity_state = EditorState.dev_tick_storage.get(name, None)
                dev_state.is_entity_selected = name in EditorState.selected_entities

                try:
                    EditorState.dev_tick_storage[name] = EntityTypeRegistry.dev_types[en[0]](entity_state, dev_state, en[1])

                except Exception as e:
                    EditorState.dev_tick_errors[name] = f"{type(e)} exception raised in dev tick: {e}\n{traceback.format_exc()}"
                    EditorState.dev_tick_storage.pop(name, None) # discard possibly unusable editor state

                del entity_state # delete the ref, so it might get cleaned up if deleted (causes issued if it's the last entity in the map)

            tt = time.perf_counter() - GameState.current_time

            # == frame ==

            # cute world origin indicator
            gizmo.draw_line(Vec3(0, 0, 0), Vec3(.2, 0, 0), Vec3(.35, .05, .05), Vec3(1, 0, 0))
            gizmo.draw_line(Vec3(0, 0, 0), Vec3(0, .2, 0), Vec3(.05, .35, .05), Vec3(0, 1, 0))
            gizmo.draw_line(Vec3(0, 0, 0), Vec3(0, 0, .2), Vec3(.05, .05, .35), Vec3(0, 0, 1))

            GameState.renderer.frame(GameState.active_camera, GameState.active_scene)

            GameState.cpu_tick_time = tt # delayed by a frame to match cpu_render_time
            GameState.cpu_render_time = GameState.renderer.cpu_frame_time

    except Exception: # all-catch crash handler, just try to backup unsaved data before crashing
        exception_backup_save()
        raise