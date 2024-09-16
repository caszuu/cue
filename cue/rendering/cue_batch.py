import OpenGL.GL as gl
import numpy as np
from .cue_resources import GPUMesh, ShaderPipeline

from ..components.cue_transform import Transform
from .. import cue_utils as utils

# == cue rendering instances ==

# rendering batch contain semi-local runtime buffers
# for each object being instanced (mesh, point, etc.)

class DrawBatch:
    __slots__ = ["mesh", "model_mat_loc", "model_transform", "draw_state", "mesh_vbo", "mesh_ebo", "draw_count"]

    # TODO: add instancing

    def __init__(self, mesh: GPUMesh, pipeline: ShaderPipeline, trans: Transform | None) -> None:
        self.mesh_vbo = mesh.mesh_vbo
        self.mesh_ebo = mesh.mesh_ebo
        self.draw_state = (mesh.mesh_vao, pipeline)

        self.draw_count = mesh.element_count if self.mesh_ebo != -1 else mesh.vertex_count

        self.model_mat_loc = -1
        if not trans is None:
            self.model_transform = trans
            self.model_mat_loc = gl.glGetUniformLocation(pipeline.shader_program, "cue_model_mat")

            if self.model_mat_loc == -1:
                utils.warn(f"[DrawBatch] A Transform was supplied but shader \"{pipeline.shader_name}\" doesn't use it")

    def draw(self) -> None:
        if self.model_mat_loc != -1:
            gl.glUniformMatrix4fv(self.model_mat_loc, 1, True, self.model_transform._trans_matrix)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.mesh_vbo)

        if self.mesh_ebo != -1:
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.mesh_ebo)
            gl.glDrawElements(gl.GL_TRIANGLES, self.draw_count, gl.GL_UNSIGNED_INT, 0)
            return

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.draw_count)

    mesh_vbo: int
    mesh_ebo: int

    model_mat_loc: int
    model_transform: Transform | None

    # required by RenderScene for sorting
    draw_state: tuple[np.uint32, ShaderPipeline]

    # draw_count will mostly be the same as mesh.vertex_count, but can differ (eg. with vertex shaders generation their own data)
    draw_count: np.uint32
