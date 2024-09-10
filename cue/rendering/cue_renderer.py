import pygame as pg
import OpenGL.GL as gl

import imgui

from .cue_camera import Camera
from ..im2d.imgui_integ import CueImguiContext

import time

# == cue OpenGL renderer backend ==

class PostPass:
    __slots__ = []

    def dispatch(self) -> None:
        raise NotImplemented

    def recreate(self) -> None:
        pass

# == top-level renderer implemetation ==

# Rendering backend TODOs:
# TODO: double-buffering (both CueRenderer and RenderTargets)

class CueRenderer:
    __slots__ = ["win_surf", "win_res", "win_aspect", "model_vao", "post_passes", "fullscreen_imgui_ctx"]

    def __init__(self, res: tuple[int, int] = (0, 0), fullscreen: bool = False, vsync: bool = True) -> None:
        pg.init()

        # setup opengl attribs

        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)

        # init window

        self.win_surf = pg.display.set_mode(res, pg.OPENGL | pg.DOUBLEBUF | pg.RESIZABLE, vsync=vsync)

        if fullscreen:
            pg.display.toggle_fullscreen()
        
        self.win_res = self.win_surf.get_size()
        self.win_aspect = self.win_res[0] / self.win_res[1]
        self.fullscreen_imgui_ctx = CueImguiContext(self.win_res)

        self.post_passes = []

        self._setup_vao()

    def _setup_vao(self):
        self.model_vao = gl.glGenVertexArrays(1)
        
        gl.glBindVertexArray(self.model_vao)
        gl.glEnableVertexAttribArray(0)

    # == post processing api ==

    def activate_post_pass(self, p: PostPass) -> None:
        self.post_passes.append(p)

    def deactivate_post_pass(self, p: PostPass) -> None:
        self.post_passes.remove(p)

    # == renderer api ==

    def frame(self, cam: Camera, scene) -> None:
        # cam stack draw

        cam.view_frame(0, scene)

        # post-process

        for p in self.post_passes:
            p.dispatch()

        self.fullscreen_imgui_ctx.set_as_current_context()

        imgui.render()
        self.fullscreen_imgui_ctx.render(imgui.get_draw_data())

        pg.display.flip()

    # OpenGL mode pygame surface (unused)
    win_surf: pg.Surface
    win_res: tuple[int, int]
    win_aspect: float

    model_vao: gl.GLuint
    particle_vao: gl.GLuint

    fullscreen_imgui_ctx: CueImguiContext
    post_passes: list[PostPass]
