import pygame.math as pm
import numpy as np
import OpenGL.GL as gl
import imgui

# from .cue_instance import MeshInstance
from src.im2d.imgui_integ import CueImguiContext
from src.cue_utils import mapped_list, mapped_refcount_list
from .cue_instance import MeshInstance
from .cue_resources import ShaderPipeline

class RenderTarget:
    def try_view_frame():
        pass

class Camera:
    __slots__ = ["cam_fov", "cam_near_plane", "cam_far_plane", "cam_proj_view_matrix", "cam_pos", "cam_dir", "active_opaque_instances", "active_non_opaque_instances", "attached_imgui_ctx", "attached_render_targets"]

    def __init__(self, fov: float = 90, near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_pos = pm.Vector3((0., 0., 0.))
        self.cam_dir = pm.Vector3((0., 0., -1.))

        self.active_opaque_instances = []
        self.active_non_opaque_instances = []

        self.attached_render_targets = mapped_refcount_list()
        self.attached_imgui_ctx = None

        self.set_settings(fov, near_plane, far_plane)

    def set_settings(self, fov: float = 90, near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_fov = fov
        self.cam_near_plane = near_plane
        self.cam_far_plane = far_plane

        self.update_cam()

    # == entity api ==

    def activate_instance(self, e: MeshInstance) -> None:
        if e.is_opaque:
            self.active_opaque_instances.append(e)
        else:
            self.active_non_opaque_instances.append(e)

        

    def deactivate_instance(self, e: MeshInstance) -> None:
        if e.is_opaque:
            self.active_opaque_instances.remove(e)
        else:
            self.active_non_opaque_instances.remove(e)

    # call after updating camera settings to apply them
    def update_cam(self) -> None:
        pass # TODO: proj view matrix calc

    def bind_cam(self, bind_loc: gl.GLuint) -> None:
        gl.glUniformMatrix4fv(bind_loc, 1, False, self.cam_proj_view_matrix)

    def project_vec(self, pos: np.ndarray) -> np.ndarray:
        raise NotImplemented # TODO

    def view_frame(self, fb: int) -> None:
        # == pre-view render targets ==

        for target in self.attached_render_targets.list_buf:
            target.try_view_frame()

        # == render camera view ==

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fb)

        # TODO: clear
        # TODO: setup camera uniform

        draw = MeshInstance.draw
        pipe_bind = ShaderPipeline.bind
        vao_bind = gl.glBindVertexArray

        # opaque pass

        for pipe in self.active_opaque_instances:
            vao_bind(pipe[0])
            pipe_bind(pipe[1])

            for ins in pipe[2]:
                draw(ins)

        # non-opaque pass
        # TODO: depth based ordering (?)

        for pipe in self.active_non_opaque_instances:
            vao_bind(pipe[0])
            pipe_bind(pipe[1])

            for ins in pipe[2]:
                draw(ins)

        # == imgui/im2d overlays ==

        ctx = self.attached_imgui_ctx
        if not ctx == None:
            ctx.set_as_current_context()

            imgui.render()
            ctx.render(imgui.get_draw_data())

    # camera settings
    cam_fov: float
    cam_near_plane: float
    cam_far_plane: float

    cam_pos: pm.Vector3
    cam_dir: np.ndarray

    # camera state
    cam_proj_view_matrix: np.ndarray

    active_opaque_instances: mapped_list[tuple[
        gl.GLuint,      # draw_vao
        ShaderPipeline, # draw_pipeline
        mapped_list[
            MeshInstance,
            int
        ]],
        int
    ]

    active_non_opaque_instances: mapped_list[tuple[
        gl.GLuint,      # draw_vao
        ShaderPipeline, # draw_pipeline
        mapped_list[
            MeshInstance,
            int
        ]],
        int
    ]

    # the imgui context that will be rendered with this camera
    # note: this context is rendered *before* the post-processing stack, for game ui
    #       use the Renderer.fullscreen_imgui_ctx which is rendered after post-processing
    attached_imgui_ctx: CueImguiContext | None

    attached_render_targets: mapped_refcount_list[RenderTarget, int]
    
