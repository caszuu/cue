from dataclasses import dataclass
from typing import Any, Callable
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

    draw_batch_setup_cb: None | Callable[[], None]
    draw_batch_restore_cb: None | Callable[[], None]

    # draw_count will mostly be the same as mesh.vertex_count / mesh.element_count, but can differ (eg. with vertex shaders generating their own data)
    draw_count: int
    draw_mode: np.uint32

class UniformBindTypes:
    FLOAT1 = 0
    FLOAT2 = 1
    FLOAT3 = 2
    FLOAT4 = 3

    SINT1 = 4
    SINT2 = 5
    SINT3 = 6
    SINT4 = 7

@dataclass(slots=True)
class UniformBind:
    bind_type: int
    bind_loc: np.uint32
    bind_value: Any

# an instance of a mesh (or other) in the RenderScene tree, these can be created and added to RenderScenes
# by external code to add new draws to the frame

@dataclass(init=False, slots=True)
class DrawInstance:
    def __init__(self, mesh: GPUMesh, pipeline: ShaderPipeline, texture_binds: tuple[GPUTexture], is_opaque: bool, uniform_data: list[UniformBind], trans: Transform | None, batch_setup_cb: None | Callable[[], None] = None, batch_restore_cb: None | Callable[[], None] = None, draw_mode: np.uint32 = gl.GL_TRIANGLES, draw_count_override: int | None = None) -> None:
        has_elements = mesh.mesh_ebo is not None
        draw_count = draw_count_override if draw_count_override is not None else (mesh.element_count if has_elements else mesh.vertex_count)
        self.draw_state = DrawState(pipeline, mesh, texture_binds, batch_setup_cb, batch_restore_cb, draw_count, draw_mode)

        self.model_transform = trans
        self.is_opaque = is_opaque

        self.uniform_data = uniform_data

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, value: object, /) -> bool:
        return id(self) == id(value)

    # non-opaque only methods

    def view_depth(self, cam_mat: np.ndarray) -> float:
        return (cam_mat @ np.array((*self.model_transform._pos, 1.), dtype=np.float32))[2]

    model_transform: Transform | None
    uniform_data: list[UniformBind]
    
    draw_state: DrawState
    is_opaque: bool

# rendering batch contain semi-local runtime buffers
# for each object being instanced (mesh, point, etc.)

UNIFORM_BIND_SET_TYPE = {
    UniformBindTypes.FLOAT1: gl.glUniform1fv,
    UniformBindTypes.FLOAT2: gl.glUniform2fv,
    UniformBindTypes.FLOAT3: gl.glUniform3fv,
    UniformBindTypes.FLOAT4: gl.glUniform4fv,

    UniformBindTypes.SINT1: gl.glUniform1iv,
    UniformBindTypes.SINT2: gl.glUniform2iv,
    UniformBindTypes.SINT3: gl.glUniform3iv,
    UniformBindTypes.SINT4: gl.glUniform4iv,
}

@dataclass(init=False, slots=True)
class DrawBatch:
    def __init__(self, state: DrawState) -> None:
        self.instance_count = 0
        self.instance_capacity = 0
        self.max_instance_capacity = 256

        self.batch_vao = state.draw_mesh.mesh_vao

        self.has_elements = state.draw_mesh.mesh_ebo is not None
        self.draw_count = state.draw_count
        self.draw_mode = state.draw_mode
        self.draw_batch_setup_cb = state.draw_batch_setup_cb
        self.draw_batch_restore_cb = state.draw_batch_restore_cb
        self.draw_state = state

        self.model_mat_buffer = []
        self.uniform_instance_data_buffer = {}
        self.model_mat_loc = gl.glGetUniformLocation(state.draw_pipeline.shader_program, "cue_model_mat")

    def draw_instance(self, ins: DrawInstance) -> None:
        gl.glBindVertexArray(self.batch_vao)

        if self.draw_batch_setup_cb is not None:
            self.draw_batch_setup_cb()

        global perfc_submit_count
        perfc_submit_count += 1

        if self.model_mat_loc != -1:
            gl.glUniformMatrix4fv(self.model_mat_loc, 1, True, ins.model_transform._trans_matrix)

        for b in ins.uniform_data:
            UNIFORM_BIND_SET_TYPE[b.bind_type](b.bind_loc, 1, b.bind_value)

        if self.has_elements:
            gl.glDrawElements(self.draw_mode, self.draw_count, gl.GL_UNSIGNED_INT, None)
        else:
            gl.glDrawArrays(self.draw_mode, 0, self.draw_count)

        if self.draw_batch_restore_cb is not None:
            self.draw_batch_restore_cb()

    # *hot* function, make fast as possible
    def append_instance(self, ins: DrawInstance) -> None:
        if ins.model_transform is not None:
            self.model_mat_buffer.append(ins.model_transform._trans_matrix)

        for b in ins.uniform_data:
            self.uniform_instance_data_buffer.setdefault(b.bind_loc, (b.bind_type, []))[1].append(b.bind_value)

        self.instance_count += 1

        if self.instance_count == self.max_instance_capacity:
            self.draw_batch() # reached instance/uniform buffer capacity, dispatch batch and reset

    def draw_batch(self) -> None:
        if not self.instance_count:
            return

        gl.glBindVertexArray(self.batch_vao)

        if self.draw_batch_setup_cb is not None:
            self.draw_batch_setup_cb()

        global perfc_submit_count
        perfc_submit_count += 1
        
        # update instance data

        if self.model_mat_loc != -1:
            gl.glUniformMatrix4fv(self.model_mat_loc, self.instance_count, True, np.concat(self.model_mat_buffer))

        for loc, data in self.uniform_instance_data_buffer.items():
            t, v = data
            UNIFORM_BIND_SET_TYPE[t](loc, self.instance_count, v)

        # dispatch instanced draw

        if self.has_elements:
            gl.glDrawElementsInstanced(self.draw_mode, self.draw_count, gl.GL_UNSIGNED_INT, None, self.instance_count)
        else:
            gl.glDrawArraysInstanced(self.draw_mode, 0, self.draw_count, self.instance_count)

        # reset batch

        if self.draw_batch_restore_cb is not None:
            self.draw_batch_restore_cb()

        self.instance_count = 0
        self.model_mat_buffer = []
        self.uniform_instance_data_buffer = {}

    instance_count: int
    instance_capacity: int
    max_instance_capacity: int
    batch_vao: np.uint32

    model_mat_buffer: list[np.ndarray]
    model_mat_loc: int
    uniform_instance_data_buffer: dict[np.uint32, tuple[int, Any]]
    
    has_elements: bool
    draw_count: int
    draw_mode: np.uint32
    draw_batch_setup_cb: None | Callable[[], None]
    draw_batch_restore_cb: None | Callable[[], None]

    draw_state: DrawState
