from dataclasses import dataclass
import time

import pygame as pg
import OpenGL.GL as gl

import imgui
import numpy as np

from .cue_camera import Camera
from .cue_scene import RenderScene
from .cue_resources import GPUTexture
from .cue_framebuffer import RenderFramebuffer, RenderAttachment
from .cue_post_pass import PostPass
from .cue_gizmos import draw_gizmos, init_gizmos
from ..im2d.imgui_integ import CueImguiContext

from . import cue_batch

from ..cue_state import GameState

# == cue OpenGL renderer backend ==

# NOTE: here we need to externaly fix pyOpenGL as it's missing one enum in it's internal lookup table, this is gross but probaly the only way
from OpenGL import images as pygl_images
pygl_images.TYPE_TO_ARRAYTYPE[gl.GL_UNSIGNED_INT_24_8] = gl.GL_UNSIGNED_INT

# Rendering backend TODOs:
# TODO: double-buffering (both CueRenderer and RenderTargets)

@dataclass(init=False, slots=True)
class CueRenderer:
    def __init__(self, res: tuple[int, int] = (0, 0), fullscreen: bool = False, vsync: bool = True) -> None:
        pg.init()

        # setup opengl attribs

        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)

        # init window

        self.win_surf = pg.display.set_mode(res, pg.OPENGL | pg.DOUBLEBUF | pg.RESIZABLE, vsync=vsync)

        if fullscreen:
            pg.display.toggle_fullscreen()
        
        self.win_res = self.win_surf.get_size()
        self.win_aspect = self.win_res[0] / self.win_res[1]
        self.fullscreen_imgui_ctx = CueImguiContext(self.win_res)

        self.offscreen_depth_buf = GPUTexture()
        self.offscreen_depth_buf.init_null(self.win_res, gl.GL_DEPTH_STENCIL, gl.GL_UNSIGNED_INT_24_8, gl.GL_DEPTH24_STENCIL8)

        self.offscreen_attachments = [
            RenderAttachment(gl.GL_COLOR_ATTACHMENT0, gl.GL_FLOAT, gl.GL_RGB, gl.GL_R11F_G11F_B10F), # render main pass in HDR
            RenderAttachment(gl.GL_COLOR_ATTACHMENT1, gl.GL_FLOAT, gl.GL_RGB, gl.GL_R11F_G11F_B10F), # bloom pass buffer
            RenderAttachment(gl.GL_DEPTH_ATTACHMENT, external_tex=self.offscreen_depth_buf),
        ]
        self.offscreen_fbs = []

        self.post_passes = []
        self.cpu_frame_time = 0.
        self.draw_call_count = 0

        GameState.static_sequencer.on_event(pg.VIDEORESIZE, self._on_resize)
        init_gizmos()

    # == post processing api ==

    def activate_post_pass(self, p: PostPass) -> None:
        self.offscreen_fbs.append(RenderFramebuffer(self.win_res, self.offscreen_attachments))
        self.post_passes.append(p)

    def deactivate_post_pass(self, p: PostPass) -> None:
        self.offscreen_fbs.pop()
        self.post_passes.remove(p)

    # == renderer api ==

    def frame(self, cam: Camera, scene: RenderScene) -> None:
        t = time.perf_counter()

        self.draw_call_count = cue_batch.perfc_submit_count
        cue_batch.perfc_submit_count = 0

        # cam stack draw

        main_pass_fb = self.offscreen_fbs[0].fb_handle if self.offscreen_fbs else np.uint32(0)

        cam.view_frame(main_pass_fb, scene)

        # post-process

        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_CULL_FACE)

        for i, p in enumerate(self.post_passes):
            if i + 1 == len(self.offscreen_fbs):
                p.dispatch(self.offscreen_fbs[i], np.uint32(0)) # final post-pass, draw to window fb
                continue
            
            p.dispatch(self.offscreen_fbs[i], self.offscreen_fbs[i + 1].fb_handle)

        # draw debug gizmos
        draw_gizmos()

        # render fullscreen ui
        self.fullscreen_imgui_ctx.set_as_current_context()

        imgui.render()
        self.fullscreen_imgui_ctx.render(imgui.get_draw_data())

        # note: do not include flip() as that waits for the gpu
        self.cpu_frame_time = time.perf_counter() - t

        pg.display.flip()

    def _on_resize(self, e) -> None:
        self.win_res = e.size
        self.win_aspect = e.size[0] / e.size[1]

        self.offscreen_depth_buf.init_null(self.win_res, gl.GL_DEPTH_STENCIL, gl.GL_UNSIGNED_INT_24_8, gl.GL_DEPTH24_STENCIL8)
        for i in range(len(self.offscreen_fbs)):
            self.offscreen_fbs[i] = RenderFramebuffer(self.win_res, self.offscreen_attachments)

        for p in self.post_passes:
            p.resize(e.size)

        self.fullscreen_imgui_ctx.resize_display(e.size)
        GameState.static_sequencer.on_event(pg.VIDEORESIZE, self._on_resize)

    # OpenGL mode pygame surface (unused)
    win_surf: pg.Surface
    win_res: tuple[int, int]
    win_aspect: float

    fullscreen_imgui_ctx: CueImguiContext

    offscreen_fbs: list[RenderFramebuffer]

    # all offscreen_fbs own their own color bufs (for post passes) bus share a single depth buffer (which is read-only in post passes)
    offscreen_depth_buf: GPUTexture
    offscreen_attachments: list[RenderAttachment]

    post_passes: list[PostPass]

    cpu_frame_time: float
    draw_call_count: int