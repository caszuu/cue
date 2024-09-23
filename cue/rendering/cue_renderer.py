import pygame as pg
import OpenGL.GL as gl

import imgui
import numpy as np

from .cue_camera import Camera
from .cue_scene import RenderScene
from .cue_gizmos import draw_gizmos, init_gizmos
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
    __slots__ = ["win_surf", "win_res", "win_aspect", "model_vao", "post_passes", "fullscreen_imgui_ctx", "cpu_frame_time"]

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
        self.cpu_frame_time = 0.

        self._setup_vao()
        init_gizmos()

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

    def frame(self, cam: Camera, scene: RenderScene) -> None:
        t = time.perf_counter()

        # cam stack draw

        cam.view_frame(0, scene)
        draw_gizmos() # draw debug gizmos

        # post-process

        for p in self.post_passes:
            p.dispatch()

        self.fullscreen_imgui_ctx.set_as_current_context()

        imgui.render()
        self.fullscreen_imgui_ctx.render(imgui.get_draw_data())

        # note: do not include flip() as that waits for the gpu
        self.cpu_frame_time = time.perf_counter() - t

        pg.display.flip()

    def on_resize(self, res: tuple[int, int]) -> None:
        self.win_res = res
        self.win_aspect = res[0] / res[1]

    # OpenGL mode pygame surface (unused)
    win_surf: pg.Surface
    win_res: tuple[int, int]
    win_aspect: float

    model_vao: np.uint32
    particle_vao: np.uint32

    fullscreen_imgui_ctx: CueImguiContext
    post_passes: list[PostPass]

    cpu_frame_time: float