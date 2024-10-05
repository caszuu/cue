import pygame.math as pm
import numpy as np
import OpenGL.GL as gl
import imgui

import math
from typing import Any
from dataclasses import dataclass

from ..im2d.imgui_integ import CueImguiContext
from .. import cue_utils as utils

# note: non-cycle-causing import only for type hints
from . import cue_scene as sc

CAMERA_UNIFORM_SIZE = 4 * 4 * np.dtype('float32').itemsize

@dataclass(init=False, slots=True)
class Camera:
    def __init__(self, aspect_ratio: float, fov: float = 90, near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_pos = pm.Vector3((0., 0., 0.))
        self.cam_rot = pm.Vector3((0., 0., 0.))

        self.attached_imgui_ctx = None

        self.cam_ubo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, self.cam_ubo)
        gl.glBufferData(gl.GL_UNIFORM_BUFFER, CAMERA_UNIFORM_SIZE, None, gl.GL_DYNAMIC_DRAW)

        self.set_perspective(aspect_ratio, fov, near_plane, far_plane)
        self.set_view(pm.Vector3((0., 0., 0.)), pm.Vector3((0., 0., 0.)))

        self.cam_clear_bits = gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT
        self.cam_clear_color = (0., 0., 0., 0.)
        self.cam_clear_depth = 1.

    def __del__(self) -> None:
        gl.glDeleteBuffers(1, np.array([self.cam_ubo]))

    # == projection / view matrix api ==
    # all matrix formulas taken from: https://songho.ca/opengl/gl_projectionmatrix.html

    def set_perspective(self, aspect_ratio: float, fov_y: float = 90, near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_fov = fov_y
        self.cam_near_plane = near_plane
        self.cam_far_plane = far_plane

        # projection matrix

        fov_tan = math.tan(math.radians(fov_y / 2))
        top = near_plane * fov_tan
        right = top * aspect_ratio

        self.cam_proj_mat = np.array([
            [near_plane / right, 0, 0, 0],
            [0, near_plane / top, 0, 0],
            [0, 0, -(far_plane + near_plane) / (far_plane - near_plane), -(2 * far_plane * near_plane) / (far_plane - near_plane)],
            [0, 0, -1, 0],
        ], dtype=np.float32)

    def set_orthographic(self, view_size: tuple[float, float], near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_fov = None # fov is invalid for orthographic
        self.cam_near_plane = near_plane
        self.cam_far_plane = far_plane

        z_div = -(far_plane / near_plane)

        self.cam_proj_mat = np.array([[1 / view_size[0], 0, 0, 0],
            [0, 1 / view_size[1], 0, 0],
            [0, 0, 2 / z_div, (far_plane + near_plane) / z_div],
            [0, 0, 0, 1]
        ], dtype=np.float32)

    # change the aspect without changing any other settings
    def re_aspect(self, aspect: float) -> None:
        if self.cam_fov is None:
            return # orthographic doesn't rely on aspect ratio (maybe a TODO?)

        self.set_perspective(aspect, self.cam_fov, self.cam_near_plane, self.cam_far_plane)

    def set_view(self, pos: pm.Vector3, rot: pm.Vector3) -> None:
        self.cam_view_proj_matrix = (
            self.cam_proj_mat @
            utils.mat4_rotate(rot.x, (1., 0., 0.)) @
            utils.mat4_rotate(rot.y, (0., -1., 0.)) @
            utils.mat4_rotate(rot.z, (0., 0., 1.)) @
            utils.mat4_translate(-pos)
        )

        gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, self.cam_ubo)
        gl.glBufferSubData(gl.GL_UNIFORM_BUFFER, 0, np.transpose(self.cam_view_proj_matrix))

    # == camera api ==

    def view_frame(self, fb: int, scene: 'sc.RenderScene') -> None:
        # == pre-view render targets ==

        scene.try_view_deps()

        # == render camera view ==

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fb)
        gl.glEnable(gl.GL_DEPTH_TEST)

        gl.glBindBufferBase(gl.GL_UNIFORM_BUFFER, 1, self.cam_ubo)

        if self.cam_clear_color is not None:
            gl.glClearColor(*self.cam_clear_color)
        if self.cam_clear_depth is not None:
            gl.glClearDepth(self.cam_clear_depth)

        gl.glClear(self.cam_clear_bits)

        scene.frame()

        # == imgui/im2d overlays ==

        ctx = self.attached_imgui_ctx
        if not ctx == None:
            ctx.set_as_current_context()

            imgui.render()
            ctx.render(imgui.get_draw_data())

    # camera settings
    cam_fov: float | None # is None when in orthographic mode
    cam_near_plane: float
    cam_far_plane: float

    cam_clear_bits: Any
    cam_clear_color: tuple[float, float, float, float] | None
    cam_clear_depth: float | None

    # note: do *not* modify these directly, use set_view() to change camera pos and dir
    cam_pos: pm.Vector3
    cam_rot: pm.Vector3

    # camera state
    cam_proj_mat: np.ndarray
    cam_view_proj_matrix: np.ndarray

    cam_ubo: np.uint32

    # the imgui context that will be rendered with this camera
    # note: this context is rendered *before* the post-processing stack, for game ui
    #       use the Renderer.fullscreen_imgui_ctx which is rendered after post-processing
    attached_imgui_ctx: CueImguiContext | None    
