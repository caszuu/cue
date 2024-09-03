import pygame.math as pm
import numpy as np
import OpenGL.GL as gl
import imgui

import math

from im2d.imgui_integ import CueImguiContext
from .cue_resources import ShaderPipeline
from .cue_batch import MeshBatch

# note: non-cycle-causing import only for type hints
from . import cue_scene as sc

class Camera:
    __slots__ = ["cam_fov", "cam_near_plane", "cam_far_plane", "cam_proj_mat", "cam_proj_view_matrix", "cam_pos", "cam_dir", "attached_imgui_ctx"]

    def __init__(self, aspect_ratio: float, fov: float = 90, near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_pos = pm.Vector3((0., 0., 0.))
        self.cam_dir = pm.Vector3((0., 0., -1.))

        self.attached_imgui_ctx = None

        self.set_perspective(aspect_ratio, fov, near_plane, far_plane)
        self.set_view(pm.Vector3((0., 0., 0.)), pm.Vector3((0., 0., -1.)))

    # == projection / view matrix api ==
    # all matrix formulas taken from: https://songho.ca/opengl/gl_projectionmatrix.html

    def set_perspective(self, aspect_ratio: float, fov: float = 90, near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_fov = fov
        self.cam_near_plane = near_plane
        self.cam_far_plane = far_plane

        # projection matrix

        fov_tan = math.tan(fov / 2)
        right = near_plane * fov_tan
        top = right / aspect_ratio

        self.cam_proj_mat = np.array([[near_plane / right, 0, 0, 0],
                             [0, near_plane / top, 0, 0],
                             [0, 0, -(far_plane + near_plane) / (far_plane - near_plane), -(2 * far_plane * near_plane) / (far_plane - near_plane)],
                             [0, 0, -1, 0]], dtype=np.dtypes.Float32DType)

    def set_orthographic(self, view_size: tuple[float, float], near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_fov = None # fov is invalid for orthographic
        self.cam_near_plane = near_plane
        self.cam_far_plane = far_plane

        z_div = -(far_plane / near_plane)

        self.cam_proj_mat = np.array([[1 / view_size[0], 0, 0, 0],
                             [0, 1 / view_size[1], 0, 0],
                             [0, 0, 2 / z_div, (far_plane + near_plane) / z_div],
                             [0, 0, 0, 1]])

    def set_view(self, pos: pm.Vector3, dir: pm.Vector3) -> None:
        pass

    # == camera api ==

    def bind_cam(self, bind_loc: gl.GLuint) -> None:
        gl.glUniformMatrix4fv(bind_loc, 1, False, self.cam_proj_view_matrix)

    def view_frame(self, fb: int, scene: 'sc.RenderScene') -> None:
        # == pre-view render targets ==

        scene.try_view_deps()

        # == render camera view ==

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fb)

        # TODO: clear
        # TODO: setup camera uniform

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

    # note: do *not* modify these directly, use set_view() to change camera pos and dir
    cam_pos: pm.Vector3
    cam_dir: np.ndarray

    # camera state
    cam_proj_mat: np.ndarray
    cam_proj_view_matrix: np.ndarray

    # the imgui context that will be rendered with this camera
    # note: this context is rendered *before* the post-processing stack, for game ui
    #       use the Renderer.fullscreen_imgui_ctx which is rendered after post-processing
    attached_imgui_ctx: CueImguiContext | None    
