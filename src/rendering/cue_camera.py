import pygame.math as pm
import numpy as np
import OpenGL.GL as gl
import imgui

# from .cue_instance import MeshInstance
from src.im2d.imgui_integ import CueImguiContext
from src.cue_utils import mapped_list, mapped_refcount_list

class MeshInstance:
    def draw(e):
        pass

class RenderTarget:
    def try_view_frame():
        pass

class Camera:
    __slots__ = ["cam_fov", "cam_near_plane", "cam_far_plane", "cam_proj_view_matrix", "cam_pos", "cam_dir", "active_opaque_entities", "active_non_opaque_entities", "active_imgui_contexts", "attached_render_targets"]

    def __init__(self, fov: float = 90, near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_pos = pm.Vector3((0., 0., 0.))
        self.cam_dir = pm.Vector3((0., 0., -1.))

        self.active_opaque_entities = []
        self.active_non_opaque_entities = []

        self.attached_render_targets = mapped_refcount_list()
        self.active_imgui_contexts = []

        self.set_settings(fov, near_plane, far_plane)

    def set_settings(self, fov: float = 90, near_plane: float = .1, far_plane: float = 100) -> None:
        self.cam_fov = fov
        self.cam_near_plane = near_plane
        self.cam_far_plane = far_plane

        self.update_cam()

    # == entity api ==

    def activate_entity(self, e: MeshInstance) -> None:
        if e.is_opaque:
            self.active_opaque_entities.append(e)
        else:
            self.active_non_opaque_entities.append(e)

    def deactivate_entity(self, e: MeshInstance) -> None:
        if e.is_opaque:
            self.active_opaque_entities.remove(e)
        else:
            self.active_non_opaque_entities.remove(e)

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

        # opaque pass

        draw = MeshInstance.draw
        for e in self.active_opaque_entities:
            draw(e)

        # non-opaque pass
        # TODO: depth based ordering (?)

        for e in self.active_non_opaque_entities:
            draw(e)

        # == imgui/im2d overlays ==

        set_ctx = CueImguiContext.set_as_current_context
        imgui_render = imgui.render
        get_draw_data = imgui.get_draw_data
        ctx_render = CueImguiContext.render

        for ctx in self.active_imgui_contexts:
            set_ctx(ctx)

            imgui_render()
            ctx_render(get_draw_data())

    # camera settings
    cam_fov: float
    cam_near_plane: float
    cam_far_plane: float

    cam_pos: pm.Vector3
    cam_dir: np.ndarray

    # camera state
    cam_proj_view_matrix: np.ndarray

    active_opaque_entities: list[MeshInstance]
    active_non_opaque_entities: list[MeshInstance]
    active_imgui_contexts: list[CueImguiContext]

    attached_render_targets: mapped_refcount_list[RenderTarget, int]
    
