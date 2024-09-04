import OpenGL.GL as GL
import pygame as pg

import imgui
from imgui.integrations.opengl import ProgrammablePipelineRenderer

# == cue/imgui integration ==

# CueImguiContext - a modified version of the pyimgui's PygameRenderer
#                   to be more explicit and based on the OpenGL Core profile

class CueImguiContext(ProgrammablePipelineRenderer):
    __slots__ = ["_ctx", "custom_key_map", "io"]

    # TODO: allow effects with custom shaders
    
    # note: creates it's own exclusive imgui context
    def __init__(self, size: tuple[int, int]) -> None:
        # store current context
        last_ctx = imgui.get_current_context()

        # create a new context, make it current and setup
        self._ctx = imgui.create_context()
        imgui.set_current_context(self._ctx)
        imgui.get_io().display_size = size
        
        super(CueImguiContext, self).__init__()

        self.custom_key_map = {}
        self._map_keys()

        # restore last current context
        imgui.set_current_context(last_ctx)

    def _custom_key(self, key) -> None:
        # We need to go to custom keycode since imgui only support keycod from 0..512 or -1
        if not key in self.custom_key_map:
            self.custom_key_map[key] = len(self.custom_key_map)
        return self.custom_key_map[key]

    def _map_keys(self) -> None:
        key_map = self.io.key_map

        key_map[imgui.KEY_TAB] = self._custom_key(pg.K_TAB)
        key_map[imgui.KEY_LEFT_ARROW] = self._custom_key(pg.K_LEFT)
        key_map[imgui.KEY_RIGHT_ARROW] = self._custom_key(pg.K_RIGHT)
        key_map[imgui.KEY_UP_ARROW] = self._custom_key(pg.K_UP)
        key_map[imgui.KEY_DOWN_ARROW] = self._custom_key(pg.K_DOWN)
        key_map[imgui.KEY_PAGE_UP] = self._custom_key(pg.K_PAGEUP)
        key_map[imgui.KEY_PAGE_DOWN] = self._custom_key(pg.K_PAGEDOWN)
        key_map[imgui.KEY_HOME] = self._custom_key(pg.K_HOME)
        key_map[imgui.KEY_END] = self._custom_key(pg.K_END)
        key_map[imgui.KEY_INSERT] = self._custom_key(pg.K_INSERT)
        key_map[imgui.KEY_DELETE] = self._custom_key(pg.K_DELETE)
        key_map[imgui.KEY_BACKSPACE] = self._custom_key(pg.K_BACKSPACE)
        key_map[imgui.KEY_SPACE] = self._custom_key(pg.K_SPACE)
        key_map[imgui.KEY_ENTER] = self._custom_key(pg.K_RETURN)
        key_map[imgui.KEY_ESCAPE] = self._custom_key(pg.K_ESCAPE)
        key_map[imgui.KEY_PAD_ENTER] = self._custom_key(pg.K_KP_ENTER)
        key_map[imgui.KEY_A] = self._custom_key(pg.K_a)
        key_map[imgui.KEY_C] = self._custom_key(pg.K_c)
        key_map[imgui.KEY_V] = self._custom_key(pg.K_v)
        key_map[imgui.KEY_X] = self._custom_key(pg.K_x)
        key_map[imgui.KEY_Y] = self._custom_key(pg.K_y)
        key_map[imgui.KEY_Z] = self._custom_key(pg.K_z)

    def set_as_current_context(self):
        imgui.set_current_context(self._ctx)

    def set_mouse_input(self, pos: tuple[int, int]) -> None:
        self.io.mouse_pos = pos
        
    def resize_display(self, size: tuple[int, int]) -> None:
        self.refresh_font_texture()
        self.io.display_size = size

    def process_key_event(self, event) -> bool:
        io = self.io

        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                io.mouse_down[0] = 1
            if event.button == 2:
                io.mouse_down[1] = 1
            if event.button == 3:
                io.mouse_down[2] = 1
            return True 

        if event.type == pg.MOUSEBUTTONUP:
            if event.button == 1:
                io.mouse_down[0] = 0
            if event.button == 2:
                io.mouse_down[1] = 0
            if event.button == 3:
                io.mouse_down[2] = 0
            if event.button == 4:
                io.mouse_wheel = .5
            if event.button == 5:
                io.mouse_wheel = -.5
            return True

        if event.type == pg.KEYDOWN:
            for char in event.unicode:
                code = ord(char)
                if 0 < code < 0x10000:
                    io.add_input_character(code)

            io.keys_down[self._custom_key(event.key)] = True

        if event.type == pg.KEYUP:
            io.keys_down[self._custom_key(event.key)] = False

        if event.type in (pg.KEYDOWN, pg.KEYUP):
            io.key_ctrl = (
                io.keys_down[self._custom_key(pg.K_LCTRL)] or
                io.keys_down[self._custom_key(pg.K_RCTRL)]
            )

            io.key_alt = (
                io.keys_down[self._custom_key(pg.K_LALT)] or
                io.keys_down[self._custom_key(pg.K_RALT)]
            )

            io.key_shift = (
                io.keys_down[self._custom_key(pg.K_LSHIFT)] or
                io.keys_down[self._custom_key(pg.K_RSHIFT)]
            )

            io.key_super = (
                io.keys_down[self._custom_key(pg.K_LSUPER)] or
                io.keys_down[self._custom_key(pg.K_LSUPER)]
            )
            
            return True

        return False

    def delta_time(self, delta_time):
        io = self.io
        
        io.delta_time = delta_time
        # if(io.delta_time <= 0.0): io.delta_time = 1./ 1000.
