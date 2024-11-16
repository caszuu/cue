import sys

# == Cue Utilities ==

bold_escape = "\x1b[1m"
error_escape = f"{bold_escape}\x1b[31m"
warning_escape = f"{bold_escape}\x1b[33m"
debug_escape = f"{bold_escape}\x1b[94m"
reset_escape = "\x1b[0m"

debug_col = (.2, .2, .8)
con_col = (.7, .7, .7)
warn_col = (.8, .8, .2)
error_col = (1., .35, .35)

log_buffer: list[tuple[tuple | None, str]] = []

def debug(message: str) -> None:
    print(f"[{debug_escape}debug{reset_escape}] {message}")
    log_buffer.append((debug_col, f"[debug] {message}"))

def console(cmd: str) -> None:
    print(f"[{bold_escape}user{reset_escape}] {cmd}")
    log_buffer.append((con_col, f"[user] {cmd}"))

def info(message: str) -> None:
    print(f"[{bold_escape}info{reset_escape}] {message}")
    log_buffer.append((None, f"[info] {message}"))

def warn(message: str) -> None:
    print(f"[{warning_escape}warn{reset_escape}] {message}")
    log_buffer.append((warn_col, f"[warn] {message}"))

def error(message: str) -> None:
    print(f"[{error_escape}error{reset_escape}] {message}")
    log_buffer.append((error_col, f"[error] {message}"))

# matrix transform utils
# again everything is sourced from https://songho.ca/index.html or https://en.wikipedia.org/wiki/Rotation_matrix

import numpy as np
import math

def mat4_translate(offset: tuple[float, float, float]) -> np.ndarray:
    x, y, z = offset
    
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1],
    ], dtype=np.float32)

def mat4_scale(scale: tuple[float, float, float]) -> np.ndarray:
    x, y, z = scale
    
    return np.array([
        [x, 0, 0, 0],
        [0, y, 0, 0],
        [0, 0, z, 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)

def mat4_rotate(axes: tuple[float, float, float]) -> np.ndarray:
    x, y, z = axes
    
    sx = math.sin(x)
    cx = math.cos(x)

    sy = math.sin(-y)
    cy = math.cos(-y)

    sz = math.sin(z)
    cz = math.cos(z)

    return np.array([
        [cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz, 0],
        [cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz, 0],
        [-sy, sx * cy, cx * cy, 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)

def mat4_rotate_axis(angle: float, axis: tuple[float, float, float]) -> np.ndarray:
    x = axis[0]
    y = axis[1]
    z = axis[2]

    s = math.sin(angle)
    c = math.cos(angle)
    nc = 1 - c

    # pain
    return np.array([
        [nc * (x ** 2) + c, nc * x * y - s * z, nc * x * z + s * y, 0],
        [nc * x * y + s * z, nc * (y ** 2) + c, nc * y * z - s * x, 0],
        [nc * x * z - s * y, nc * y * z + s * x, nc * (z ** 2) + c, 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)

# == dev utils ==

import imgui

# a imgui.begin helper that will add "overlay-like" attribs, can be used inplace of a imgui.begin
def begin_dev_overlay(id: str, corner: int = 0, flags: int = 0):
    overlay_flags = imgui.WINDOW_NO_DECORATION | imgui.WINDOW_ALWAYS_AUTO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS | imgui.WINDOW_NO_FOCUS_ON_APPEARING | imgui.WINDOW_NO_NAV | imgui.WINDOW_NO_MOVE
    pad = 10

    viewport = imgui.get_main_viewport()
    win_pos_x = viewport.work_pos.x + viewport.work_size.x - pad if (corner & 1) else viewport.work_pos.x + pad
    win_pos_y = viewport.work_pos.y + viewport.work_size.y - pad if (corner & 2) else viewport.work_pos.y + pad

    imgui.set_next_window_position(win_pos_x, win_pos_y, pivot_x=1. if (corner & 1) else 0., pivot_y=1. if (corner & 2) else 0.)
    imgui.set_next_window_bg_alpha(.35)

    return imgui.begin(id, flags=overlay_flags | flags)

from .cue_state import GameState
from typing import Callable

cmd_buffer: str = ""
cmd_callbacks: dict[str, Callable[[list[str]], None]] = {}

# a simple developer console, returns if the console is still open
def show_developer_console() -> bool:
    global cmd_buffer
    GameState.renderer.fullscreen_imgui_ctx.set_as_current_context()

    if not imgui.begin("Dev Console", closable=True)[1]:
        imgui.end()
        return False
    
    # scroll box

    height_reserve = imgui.get_style().item_spacing.y + imgui.get_frame_height_with_spacing()
    with imgui.begin_child("ScrollBox", height=-height_reserve, border=True, flags=imgui.WINDOW_HORIZONTAL_SCROLLING_BAR):
        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (4, 2))

        for line in log_buffer:            
            if line[0] is not None:
                imgui.push_style_color(imgui.COLOR_TEXT, *line[0])

            imgui.text_unformatted(line[1])

            if line[0] is not None:
                imgui.pop_style_color()
            
        if imgui.get_scroll_y() >= imgui.get_scroll_max_y():
            imgui.set_scroll_here_y(1.)

        imgui.pop_style_var()

    imgui.separator()

    # console prompt

    input_flags = imgui.INPUT_TEXT_ENTER_RETURNS_TRUE | imgui.INPUT_TEXT_CALLBACK_COMPLETION | imgui.INPUT_TEXT_CALLBACK_HISTORY
    enter_input, cmd_buffer = imgui.input_text("Command Input", cmd_buffer, flags=input_flags)

    if enter_input:
        cmd_parts = cmd_buffer.strip().split(' ')

        if cmd_buffer.strip() != "":
            cb = cmd_callbacks.get(cmd_parts[0], None)
            if cb is None:
                error(f"No command named \"{cmd_parts[0]}\" found")
            else:
                console(f"{cmd_buffer}")
                cb(cmd_parts[1:])

            cmd_buffer = ""
    
    imgui.set_item_default_focus()
    if enter_input:
        imgui.set_keyboard_focus_here(-1)

    imgui.end()
    return True

def add_dev_command(cmd: str, cb: Callable[[list[str]], None]):
    if cmd in cmd_callbacks:
        raise ValueError(f"The command \"{cmd}\" was already added!")
    
    cmd_callbacks[cmd] = cb

def show_perf_overlay(corner: int = 0):
    win_flags = imgui.WINDOW_NO_DECORATION | imgui.WINDOW_ALWAYS_AUTO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS | imgui.WINDOW_NO_FOCUS_ON_APPEARING | imgui.WINDOW_NO_NAV | imgui.WINDOW_NO_MOVE
    pad = 10

    viewport = imgui.get_main_viewport()
    win_pos_x = viewport.work_pos.x + viewport.work_size.x - pad if (corner & 1) else viewport.work_pos.x + pad
    win_pos_y = viewport.work_pos.y + viewport.work_size.y - pad if (corner & 2) else viewport.work_pos.y + pad

    imgui.set_next_window_position(win_pos_x, win_pos_y, pivot_x=1. if (corner & 1) else 0., pivot_y=1. if (corner & 2) else 0.)
    imgui.set_next_window_bg_alpha(.35)

    with imgui.begin("Perf overlay", flags=win_flags):
        imgui.text("Performace overlay")
        imgui.separator()

        imgui.text(f"Frame time: {round(GameState.delta_time * 1000, 2)}ms")

        imgui.spacing(); imgui.spacing()

        imgui.text(f"Tick time: {round(GameState.cpu_tick_time * 1000, 2)}ms")
        imgui.text(f"Cpu render time: {round(GameState.cpu_render_time * 1000, 2)}ms")

        imgui.spacing(); imgui.spacing()

        imgui.text(f"Draw call count: {GameState.renderer.draw_call_count}")