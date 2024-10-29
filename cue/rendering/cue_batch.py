from dataclasses import dataclass
import OpenGL.GL as gl
import numpy as np
from .cue_resources import GPUMesh, GPUTexture, ShaderPipeline

from ..components.cue_transform import Transform
from .. import cue_utils as utils

# == cue rendering instances ==

# perf counters

perfc_submit_count = 0

# represents the opengl state that can differ between DrawBatches, ideally
# if two DrawInstances have the same DrawState, they should be valid to merge

@dataclass(slots=True, frozen=True)
class DrawState:
    draw_pipeline: ShaderPipeline
    draw_mesh: GPUMesh
    draw_texture_binds: tuple[GPUTexture]

    # draw_count will mostly be the same as mesh.vertex_count, but can differ (eg. with vertex shaders generating their own data)
    draw_count: int

# an instance of a mesh (or other) in the RenderScene tree, these can be created and added to RenderScenes
# by external code to add new draws to the frame

@dataclass(init=False, slots=True)
class DrawInstance:
    def __init__(self, mesh: GPUMesh, pipeline: ShaderPipeline, texture_binds: tuple[GPUTexture], is_opaque: bool, trans: Transform | None, draw_count_override: int | None = None) -> None:
        has_elements = mesh.mesh_ebo is not None
        draw_count = draw_count_override if draw_count_override is not None else (mesh.element_count if has_elements else mesh.vertex_count)
        self.draw_state = DrawState(pipeline, mesh, texture_binds, draw_count)

        self.model_transform = trans
        self.is_opaque = is_opaque

    def __hash__(self) -> int:
        return hash((self.draw_state, self.model_transform))

    # non-opaque only methods

    def view_depth(self, cam_mat: np.ndarray) -> float:
        return (cam_mat @ np.array((*self.model_transform._pos, 1.), dtype=np.float32))[2]

    model_transform: Transform | None
    
    draw_state: DrawState
    is_opaque: bool

# rendering batch contain semi-local runtime buffers
# for each object being instanced (mesh, point, etc.)

@dataclass(init=False, slots=True)
class DrawBatch:
    def __init__(self, state: DrawState) -> None:
        self.instance_count = 0
        self.instance_capacity = 0
        self.max_instance_capacity = 256

        self.batch_vao = state.draw_mesh.mesh_vao

        self.has_elements = state.draw_mesh.mesh_ebo is not None
        self.draw_count = state.draw_count
        self.draw_state = state

        self.model_mat_buffer = []
        self.model_mat_loc = gl.glGetUniformLocation(state.draw_pipeline.shader_program, "cue_model_mat")

    def draw_instance(self, ins: DrawInstance) -> None:
        gl.glBindVertexArray(self.batch_vao)

        global perfc_submit_count
        perfc_submit_count += 1

        if self.model_mat_loc != -1:
            gl.glUniformMatrix4fv(self.model_mat_loc, 1, True, ins.model_transform._trans_matrix)

        if self.has_elements:
            gl.glDrawElements(gl.GL_TRIANGLES, self.draw_count, gl.GL_UNSIGNED_INT, None)
        else:
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.draw_count)

    # *hot* function, make fast as possible
    def append_instance(self, ins: DrawInstance) -> None:
        if ins.model_transform is not None:
            self.model_mat_buffer.append(ins.model_transform._trans_matrix.transpose())

        self.instance_count += 1

        if self.instance_count == self.max_instance_capacity:
            self.draw_batch() # reached instance/uniform buffer capacity, dispatch batch and reset

    def draw_batch(self) -> None:
        if not self.instance_count:
            return

        gl.glBindVertexArray(self.batch_vao)

        global perfc_submit_count
        perfc_submit_count += 1
        
        # update instance data

        if self.model_mat_loc != -1:
            gl.glUniformMatrix4fv(self.model_mat_loc, self.instance_count, False, np.concat(self.model_mat_buffer))

        # dispatch instanced draw

        if self.has_elements:
            gl.glDrawElementsInstanced(gl.GL_TRIANGLES, self.draw_count, gl.GL_UNSIGNED_INT, None, self.instance_count)
        else:
            gl.glDrawArraysInstanced(gl.GL_TRIANGLES, 0, self.draw_count, self.instance_count)

        # reset batch

        self.instance_count = 0
        self.model_mat_buffer = []

    instance_count: int
    instance_capacity: int
    max_instance_capacity: int
    batch_vao: np.uint32

    model_mat_buffer: list[np.ndarray]
    model_mat_loc: int
    
    has_elements: bool
    draw_count: int

    draw_state: DrawState
