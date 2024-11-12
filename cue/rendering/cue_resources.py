import pygame as pg
import OpenGL.GL as gl
import numpy as np

from .. import cue_utils as utils

# == Cue Resource Types (mostly rendering related) ==

class GPUMesh:
    __slots__ = ["mesh_vao", "mesh_ebo", "mesh_pos_vbo", "mesh_norm_vbo", "mesh_uv_vbo", "vertex_count", "element_count"]

    def __init__(self) -> None:
        # gen opengl buffers

        self.mesh_vao = gl.glGenVertexArrays(1)
        self.mesh_pos_vbo, self.mesh_norm_vbo, self.mesh_uv_vbo = gl.glGenBuffers(3)
        self.mesh_ebo = None

        self.vertex_count = 0
        self.element_count = 0

    def __del__(self) -> None:
        bufs = [self.mesh_pos_vbo, self.mesh_norm_vbo, self.mesh_uv_vbo]
        
        if self.mesh_ebo is not None:
            bufs += [self.mesh_ebo]

        gl.glDeleteBuffers(len(bufs), np.array(bufs))

    # mutator funcs

    def write_to(self, pos_data = None, norm_data = None, uv_data = None, vertex_count: int = 0, ebo_data = None, element_count: int = 0) -> None:
        gl.glBindVertexArray(self.mesh_vao)

        # pos

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.mesh_pos_vbo)
        if pos_data is not None:
            gl.glBufferData(gl.GL_ARRAY_BUFFER, pos_data, gl.GL_STATIC_DRAW)
            self.vertex_count = vertex_count
        
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, False, 3 * 4, None)
        gl.glEnableVertexAttribArray(0)

        # norm

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.mesh_norm_vbo)
        if norm_data is not None:
            gl.glBufferData(gl.GL_ARRAY_BUFFER, norm_data, gl.GL_STATIC_DRAW)
            self.vertex_count = vertex_count

        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, False, 3 * 4, None)
        gl.glEnableVertexAttribArray(1)

        # uvs

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.mesh_uv_vbo)
        if uv_data is not None:
            gl.glBufferData(gl.GL_ARRAY_BUFFER, uv_data, gl.GL_STATIC_DRAW)
            self.vertex_count = vertex_count

        gl.glVertexAttribPointer(2, 2, gl.GL_FLOAT, False, 2 * 4, None)
        gl.glEnableVertexAttribArray(2)

        # elems

        if ebo_data is not None:
            if self.mesh_ebo is None:
                self.mesh_ebo = gl.glGenBuffers(1)

            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.mesh_ebo)
            gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, ebo_data, gl.GL_STATIC_DRAW)
            self.element_count = element_count

        gl.glBindVertexArray(0)

    mesh_pos_vbo: np.uint32
    mesh_norm_vbo: np.uint32
    mesh_uv_vbo: np.uint32

    mesh_ebo: np.uint32 | None
    mesh_vao: np.uint32

    vertex_count: int
    element_count: int

class GPUTexture:
    __slots__ = ["texture_handle", "texture_format", "texture_size"]

    def __init__(self, mag_filter: np.uint32 = gl.GL_LINEAR, min_filter: np.uint32 = gl.GL_LINEAR, wrap: np.uint32 = gl.GL_CLAMP_TO_EDGE) -> None:
        self.texture_handle = gl.glGenTextures(1)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_handle)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, mag_filter)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, min_filter)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, wrap)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, wrap)

    def __del__(self) -> None:
        gl.glDeleteTextures(1, [self.texture_handle])

    # mutator funcs; note: binds to current active texture and leaves it bound

    def bind_to(self, texture_index):
        gl.glActiveTexture(gl.GL_TEXTURE0 + texture_index)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_handle)

    def init_null(self, size: tuple[int, int], gl_format: np.uint32, gl_type: np.uint32) -> None:
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_handle)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl_format, size[0], size[1], 0, gl_format, gl_type, None)

        self.texture_format = gl_format
        self.texture_size = size

    def write_to(self, surf: pg.Surface, gl_format: np.uint32 = gl.GL_RGBA, gl_type: np.uint32 = gl.GL_UNSIGNED_BYTE, pg_format: str = "RGBA") -> None:
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_handle)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl_format, surf.get_width(), surf.get_height(), 0, gl_format, gl_type, pg.image.tobytes(surf, pg_format, False)) # textures don't need to flip?

        self.texture_format = gl_format
        self.texture_size = surf.get_size()

    def read_back(self) -> pg.Surface:
        raise NotImplemented # would always be a performace hit, should not be generally required

    texture_handle: int

    texture_format: np.uint32
    texture_size: tuple[int, int]

class CueGLUniformBindings:
    GLOBAL = 0
    CAMERA = 1

# yes, this is a Vulkan approach to a OpenGL api resource (Programs)
# but it's still more efficient then the conventional OpenGL way
#
# note: this is not related to OpenGL program pipelines, only normal OpenGL programs are used
class ShaderPipeline:
    __slots__ = ["shader_program", "shader_name"]

    def __init__(self, vs_src: str, fs_src: str, dbg_name: str) -> None:
        def load_shader(shader_type, src):
            s = gl.glCreateShader(shader_type)

            gl.glShaderSource(s, src)
            gl.glCompileShader(s)

            result = gl.glGetShaderiv(s, gl.GL_COMPILE_STATUS)

            if not result:
                log = gl.glGetShaderInfoLog(s)

                utils.error(f"error while compiling a shader {dbg_name}: {str(log)}")

            return s
        
        vs = load_shader(gl.GL_VERTEX_SHADER, vs_src)
        fs = load_shader(gl.GL_FRAGMENT_SHADER, fs_src)

        p = gl.glCreateProgram()

        gl.glAttachShader(p, vs)
        gl.glAttachShader(p, fs)

        gl.glLinkProgram(p)
        result = gl.glGetProgramiv(p, gl.GL_LINK_STATUS)

        if not result:
            log = gl.glGetProgramInfoLog(p)

            utils.error(f"error while linking a ShaderPipeline {dbg_name}: {log}")

        self.shader_program = p
        self.shader_name = dbg_name
    
        # setup uniform block bindings

        g_loc = gl.glGetUniformBlockIndex(p, "cue_global_buf")
        if g_loc != gl.GL_INVALID_INDEX:
            gl.glUniformBlockBinding(p, g_loc, CueGLUniformBindings.GLOBAL)

        c_loc = gl.glGetUniformBlockIndex(p, "cue_camera_buf")
        if c_loc != gl.GL_INVALID_INDEX:
            gl.glUniformBlockBinding(p, c_loc, CueGLUniformBindings.CAMERA)

    def bind(self) -> None:
        gl.glUseProgram(self.shader_program)

    shader_program: np.uint32
    shader_name: str
