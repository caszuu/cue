import os, sys, time, pickle, json, traceback
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
from ..entities.cue_entity_types import DevTickError, EntityTypeRegistry

from ..rendering.cue_renderer import CueRenderer
from ..rendering.cue_camera import Camera
from ..rendering.cue_scene import RenderScene
from ..im2d.imgui_integ import CueImguiContext

from .. import cue_utils as utils
from ..rendering import cue_resources as res
from ..rendering import cue_batch as bat
from ..rendering import cue_gizmos as gizmo

from .. import cue_map as map
from .. import cue_sequence as seq

from ..components.cue_freecam import FreecamController

# == On-Cue Editor ==

EDITOR_ASSET_DIR = "assets/"

# editors global state
class EditorState:
    # == viewport state ==
        
    ui_ctx: CueImguiContext
    editor_freecam: FreecamController
    
    error_msg: str | None = None

    # == ui state ==

    is_settings_win_open: bool = False
    is_perf_overlay_open: bool = False
    is_model_importer_open: bool = False
    is_entity_tree_open: bool = False

    on_ensure_saved_success: Callable[[], None] | None = None
    entity_tree_filter: str = ""

    # == model import state ==

    assimp_scene: Any | None = None
    assimp_path: str | None = None

    assimp_sel_mesh: int = 0
    assimp_saved_msg: str | None = None

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
    selected_entity: str | None = None

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
    EditorState.selected_entity = None
    EditorState.entities_in_editing = set()
    
    reset_editor_ui()
    
    GameState.entity_storage.reset()
    GameState.sequencer = CueSequencer(time.perf_counter()) # to del all scheduled seqs
    GameState.active_scene = RenderScene()
    GameState.active_camera = Camera(GameState.renderer.win_aspect, 70)

    EditorState.editor_freecam = FreecamController(GameState.active_camera)

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
        entity_export_buf[en_name] = (en[0], en[1])

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

    EditorState.entities_in_editing.discard(old_name)
    EditorState.entities_in_editing.add(new_name)

    if EditorState.selected_entity == old_name:
        EditorState.selected_entity = new_name
    
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

        # entity header

        if imgui.is_window_focused():
            EditorState.selected_entity = en_name

        en_type, en_data = EditorState.entity_data_storage[en_name]

        imgui.push_item_width(imgui.get_content_region_available()[0] * .3)
        changed_name, new_en_name = imgui.input_text("entity name", en_name); imgui.same_line()
        changed_type, new_en_type_id = imgui.combo("entity type", EntityTypeRegistry.entity_names.index(en_type), EntityTypeRegistry.entity_names)
        imgui.pop_item_width()

        if changed_name:
            if handle_entity_rename(en_name, new_en_name):
                en_name = new_en_name

        if changed_type:
            # handle cleanup and change of the entity type
            new_en_type = EntityTypeRegistry.entity_names[new_en_type_id]
            en_data = EntityTypeRegistry.entity_types[new_en_type].default_data()

            EditorState.entity_data_storage[en_name] = (new_en_type, en_data)
            EditorState.dev_tick_storage.pop(en_name, None) # discard probably uncompatable editor state

            en_type = new_en_type

        imgui.separator()

        # entity props

        imgui.text("entity props:")
        imgui.indent()

        imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND, 0., 0., 0., 0.)

        changed_data = False

        with imgui.begin_table("Entity Properties", 2, imgui.TABLE_BORDERS | imgui.TABLE_RESIZABLE):
            imgui.table_next_row()
            imgui.table_next_column()
            imgui.text("prop")
            
            imgui.table_next_column()
            imgui.text("value")

            for prop, value in dict(en_data).items():
                imgui.push_id(prop)

                # prop name
                imgui.table_next_row()
                imgui.table_next_column()
                imgui.push_item_width(-imgui.FLOAT_MIN)

                changed_name, new_prop = imgui.input_text("##prop", prop, flags=imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
                if changed_name and not (new_prop in en_data or not new_prop):
                        # new prop name, rename it
                        en_data[new_prop] = en_data.pop(prop)
                        imgui.pop_id()
                        imgui.push_id(new_prop)
                        prop = new_prop

                changed_data |= changed_name

                imgui.pop_item_width()

                # prop value
                imgui.table_next_column()
                imgui.push_item_width(-imgui.FLOAT_MIN)

                if isinstance(value, int | float):
                    changed_val, val = imgui.drag_float("##val", value, .01)
                    en_data[prop] = val
                elif isinstance(value, Vec2):
                    changed_val, val = imgui.drag_float2("##val", value.x, value.y, .01)
                    en_data[prop] = Vec2(val)
                elif isinstance(value, Vec3):
                    changed_val, val = imgui.drag_float3("##val", value.x, value.y, value.z, .01)
                    en_data[prop] = Vec3(val)
                elif isinstance(value, str):
                    changed_val, val = imgui.input_text("##val", value)
                    en_data[prop] = val
                # elif isinstance(value, list):
                # elif isinstance(value, dict):
                else:
                    imgui.text_disabled(repr(value))
                    changed_val = False

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
            imgui.same_line()
            imgui.text_colored("(Shift+A)", .5, .5, .5, 1.)
            imgui.end_tooltip()

        # delete button

        imgui.same_line()
        if imgui.small_button("delete prop"):
            imgui.open_popup("##delete_prop")

        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text("Adds a new prop to entity props.")
            imgui.same_line()
            imgui.text_colored("(Shift+A)", .5, .5, .5, 1.)
            imgui.end_tooltip()
        
        imgui.unindent()
        
        # add menu

        if imgui.begin_popup("##add_prop"):
            imgui.text("Select prop type to add")
            imgui.separator()

            if imgui.selectable("Number")[0]:
                add_new_prop(en_data, "new_float", 0.)
                imgui.close_current_popup()

            if imgui.selectable("Vector 2")[0]:
                add_new_prop(en_data, "new_vec2", Vec2())
                imgui.close_current_popup()

            if imgui.selectable("Vector 3")[0]:
                add_new_prop(en_data, "new_vec3", Vec3())
                imgui.close_current_popup()

            if imgui.selectable("String / Path")[0]:
                add_new_prop(en_data, "new_str", "")
                imgui.close_current_popup()
            
            imgui.end_popup()

        # delete menu
        
        if imgui.begin_popup("##delete_prop"):
            imgui.text("Select prop to delete")
            imgui.separator()

            for prop in en_data.keys():
                if imgui.selectable(prop)[0]:
                    en_data.pop(prop)
                    imgui.close_current_popup()
                    break
            
            imgui.end_popup()

        imgui.spacing(); imgui.spacing()

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
            EditorState.dev_tick_errors.pop(en_name, None)
            EditorState.has_unsaved_changes = True

    else:
        # editor panel closed
        EditorState.entities_in_editing.discard(en_name)

    imgui.end()

def editor_create_entity():
    new_en = ("bt_static_mesh", EntityTypeRegistry.entity_types["bt_static_mesh"].default_data())
    en_name = f"en_new"

    if en_name in EditorState.entity_data_storage:
        i = 0
        while True:
            en_name = f"en_new_{i}"
            if not en_name in EditorState.entity_data_storage:
                break

            i += 1

    EditorState.has_unsaved_changes = True

    EditorState.entity_data_storage[en_name] = new_en
    EditorState.selected_entity = en_name

    # immidatelly open an editor for the entity
    EditorState.entities_in_editing.add(en_name)

def editor_delete_entity(next_to_select: str | None = None):
    if EditorState.selected_entity is None:
        return

    EditorState.has_unsaved_changes = True
    
    try:
        EditorState.entity_data_storage.pop(EditorState.selected_entity)
    except:
        utils.error(f"[editor] failed to delete an entity {EditorState.selected_entity}, this is a bug")
    
    EditorState.entities_in_editing.discard(EditorState.selected_entity) # close the entities editing panel if was open
    EditorState.dev_tick_storage.pop(EditorState.selected_entity, None) # cleanup dev state (if any) to save memory
    EditorState.selected_entity = next_to_select

def entity_tree_ui():
    imgui.set_next_window_size(305, 350, condition=imgui.FIRST_USE_EVER)

    with imgui.begin("Entity Tree", None):
        add_en = imgui.button("+")
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text("Create an entity"); imgui.same_line()
            imgui.text_colored("(Ctrl+a)", .5, .5, .5, 1.)
            imgui.end_tooltip()

        imgui.same_line()
        
        del_en = imgui.button("-")
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text("Delete an entity"); imgui.same_line()
            imgui.text_colored("(Ctrl+Del)", .5, .5, .5, 1.)
            imgui.end_tooltip()

        imgui.same_line()

        _, EditorState.entity_tree_filter = imgui.input_text("filter", value=EditorState.entity_tree_filter)
        filter_state = EditorState.entity_tree_filter

        next_in_filter: str | None = None
        last_was_selected: bool = False

        if imgui.begin_child("entity_tree_list", 0, 0, True):
            for name, en in EditorState.entity_data_storage.items():
                if filter_state not in name:
                    continue

                has_error = EditorState.dev_tick_errors.get(name, None) is not None
                if has_error:
                    imgui.push_style_color(imgui.COLOR_TEXT, 1., .35, .35, 1.)

                clicked, selected = imgui.selectable(name, selected=EditorState.selected_entity == name)
                if clicked:
                    EditorState.selected_entity = name if selected else None
                
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
            
        imgui.same_line()
        imgui.text(f"Model File: {None if EditorState.assimp_path is None else os.path.basename(EditorState.assimp_path)}")
        
        imgui.separator()

        with imgui.begin_tab_bar("Model Importer Tab Bar"):
            if imgui.begin_tab_item("Mesh Data")[0]:
                # mesh importer

                if EditorState.assimp_scene is not None:
                    reload_model, EditorState.assimp_sel_mesh = imgui.combo("selected mesh", EditorState.assimp_sel_mesh, [str(m) for m in EditorState.assimp_scene.meshes])
                    imgui.spacing(); imgui.spacing()

                    imgui.text(f"Mesh vertex count: {len(EditorState.assimp_scene.meshes[EditorState.assimp_sel_mesh].vertices)}")
                    imgui.text(f"Mesh index count: {len(EditorState.assimp_scene.meshes[EditorState.assimp_sel_mesh].faces) * 3}")
                else:
                    reload_model, EditorState.assimp_sel_mesh = imgui.combo("selected mesh", 0, [])
                    imgui.spacing(); imgui.spacing()

                    imgui.text(f"Mesh vertex count: No mesh")
                    imgui.text(f"Mesh index count: No mesh")

                if reload_model:
                    EditorState.assimp_saved_msg = None

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
                    
                    vert_buf[:] = mesh.vertices.flatten()
                    norm_buf[:] = mesh.normals.flatten()
                    
                    for vi in range(vert_count):
                        uv_buf[vi:vi + 2] = mesh.texturecoords[0][vi][:2] # only using the first uv coords array, assuming this is correct?

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
        imgui.text(f"Cpu render time: {round(GameState.cpu_render_time * 1000, 2)}ms")

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
            _, EditorState.is_entity_tree_open = imgui.menu_item("Entity tree", selected=EditorState.is_entity_tree_open)
            _, EditorState.is_model_importer_open = imgui.menu_item("Model importer", selected=EditorState.is_model_importer_open)

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

    for en in list(EditorState.entities_in_editing): # note: doing a copy here, as [entities_in_editing] might change mid iteration 
        entity_edit_ui(en)

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
    GameState.static_sequencer = CueSequencer(t)
    GameState.entity_storage = EntityStorage()
    GameState.asset_manager = AssetManager(EDITOR_ASSET_DIR)

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

                elif e.type == pg.QUIT:
                    should_exit = True

                GameState.sequencer.send_event_id(e.type, e)
                GameState.static_sequencer.send_event_id(e.type, e)
            
            EditorState.editor_freecam.set_capture(pg.mouse.get_pressed()[2])

            # == tick ==

            dt = time.perf_counter() - t
            t = time.perf_counter()

            EditorState.ui_ctx.set_as_current_context()
            imgui.new_frame()

            GameState.delta_time = dt
            EditorState.ui_ctx.delta_time(dt)
            
            GameState.sequencer.tick(t)
            GameState.static_sequencer.tick(t)

            if should_exit:
                ensure_map_saved(lambda: sys.exit(0))
            editor_process_ui()

            # perform dev/editor ticks
            for name, en in EditorState.entity_data_storage.items():
                if name in EditorState.dev_tick_errors:
                    continue # do not waste time ticking erroneous entities
                
                entity_state = EditorState.dev_tick_storage.get(name, None)
                dev_state = {"is_selected": name == EditorState.selected_entity}

                try:
                    EditorState.dev_tick_storage[name] = EntityTypeRegistry.dev_types[en[0]](entity_state, dev_state, en[1])
                
                except DevTickError as e:
                    EditorState.dev_tick_errors[name] = f"validation error: {e}\n{traceback.format_exc()}"
                    EditorState.dev_tick_storage.pop(name, None) # discard possibly unusable editor state

                except Exception as e:
                    EditorState.dev_tick_errors[name] = f"{type(e)} exception raised in dev tick: {e}\n{traceback.format_exc()}"
                    EditorState.dev_tick_storage.pop(name, None) # discard possibly unusable editor state

                del entity_state # delete the ref, so it might get cleaned up if deleted (causes issued if it's the last entity in the map)

            tt = time.perf_counter() - t

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
