import pygame as pg
import OpenGL.GL as gl
import numpy as np
import os
import struct

from .. import cue_utils as utils

# == Cue Resource Types (mostly rendering related) ==

class GPUMesh:
    __slots__ = ["mesh_vao", "mesh_ebo", "mesh_vbo", "vertex_count", "element_count"]

    def __init__(self, vao: gl.GLuint) -> None:
        # if not os.path.exists(path):
        #     utils.abort(f"Can't find a mesh resource in {path}")

        # load mesh data from disk

        # scene = pywavefront.Wavefront(path, strict=False)
        # scene.parse()

        # index_set = set()
        # index_buf = b''

        # for name, mesh in scene.meshes.items():
        #     # if not mesh.has_faces:
        #     #     print(f"{os.path.basename(path)}: skipping mesh {name}, does not contain faces")
        #     #     continue
            
        #     for face in mesh.faces:
        #         if len(face) != 3:
        #             print(f"{os.path.basename(path)}: skipping mesh {name}, contains non-triangle faces")
        #             continue

        #         index_buf += struct.pack("I", *face)
                
        #         for i in face:
        #             index_set.add(i)
        
        # vert_buf = b''

        # for i in index_set:
        #     vert_buf += struct.pack("f", *scene.vertices[i])

        # print(scene.vertices)

        # gen opengl buffers

        self.mesh_vao = vao
        self.mesh_vbo = gl.glGenBuffers(1)
        self.mesh_ebo = -1

        # gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.mesh_vbo)
        # gl.glBufferData(gl.GL_ARRAY_BUFFER, len(vert_buf), vert_buf, gl.GL_STATIC_DRAW)

        # gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.mesh_ebo)
        # gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, len(index_buf), index_buf, gl.GL_STATIC_DRAW)

        # # gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 3 * 4, 0)
        # gl.glEnableVertexAttribArray(0)

        self.vertex_count = 0
        self.element_count = 0

    def __del__(self) -> None:
        bufs = [self.mesh_vbo, self.mesh_ebo] if self.mesh_ebo != 1 else [self.mesh_vbo]

        gl.glDeleteBuffers(len(bufs), np.array(bufs))

    def bind(self) -> None:
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.mesh_vbo)

        if self.mesh_ebo != -1:
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.mesh_ebo)

    # mutator funcs

    def write_to(self, vbo_data = b"", vertex_count: int = 0, ebo_data = b"", element_count = 0) -> None:
        if len(vbo_data):
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.mesh_vbo)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, vbo_data, gl.GL_STATIC_DRAW)
            self.vertex_count = vertex_count

        if len(ebo_data):
            if self.mesh_ebo == -1:
                self.mesh_ebo = gl.glGenBuffers(1)

            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.mesh_ebo)
            gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, ebo_data, gl.GL_STATIC_DRAW)
            self.element_count = element_count

    mesh_vbo: gl.GLuint
    mesh_ebo: gl.GLuint
    mesh_vao: gl.GLuint

    vertex_count: int
    element_count: int

class GPUTexture:
    __slots__ = ["texture_handle", "texture_format", "texture_size"]

    def __init__(self, mag_filter: gl.GLuint = gl.GL_LINEAR, min_filter: gl.GLuint = gl.GL_LINEAR, wrap: gl.GLuint = gl.GL_CLAMP_TO_EDGE) -> None:
        self.texture_handle = gl.glGenTextures(1)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_handle)

        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, mag_filter)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, min_filter)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, wrap)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, wrap)

    def __del__(self) -> None:
        gl.glDeleteTextures(1, [self.texture_handle])

    def bind_to(self, texture_index):
        gl.glActiveTexture(texture_index)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_handle)

    # mutator funcs; note: binds to current active texture and leaves it bound

    def write_to(self, surf: pg.Surface, gl_format: gl.GLenum = gl.GL_RGBA, gl_type: gl.GLenum = gl.GL_UNSIGNED_BYTE, pg_format: str = "RGBA") -> None:
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_handle)
        
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl_format, surf.get_width(), surf.get_height(), 0, gl_format, gl.GL_UNSIGNED_BYTE, pg.image.tobytes(surf, pg_format, flipped=True))

        self.texture_format = gl_format
        self.texture_size = surf.get_size()

    def init_null(self, size: tuple[int, int], gl_format: gl.GLenum, gl_type: gl.GLenum) -> None:
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_handle)
        
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl_format, size[0], size[1], 0, gl_format, gl_type, None)

        self.texture_format = gl_format
        self.texture_size = surf.get_size()

    def read_back(self) -> pg.Surface:
        raise NotImplemented # would always be a performace hit, should not be generally required

    texture_handle: gl.GLuint

    texture_format: gl.GLuint
    texture_size: tuple[int, int]

class CueGLUniformBindings:
    GLOBAL = 0
    CAMERA = 1

# yes, this is a Vulkan approach to a OpenGL api resource (Programs)
# but it's still more efficient then the conventional OpenGL way
#
# note: this is not related to OpenGL program pipelines, only normal OpenGL programs are used
class ShaderPipeline:
    __slots__ = ["shader_program", "uniform_binds"]

    def __init__(self, vs_path: str, fs_path: str) -> None:
        if not os.path.exists(vs_path):
            utils.abort(f"Can't find a vertex shader in {vs_path}")
        
        if not os.path.exists(fs_path):
            utils.abort(f"Can't find a fragment shader in {fs_path}")

        def load_shader(shader_type, path):
            src = open(path, "r")

            s = gl.glCreateShader(shader_type)

            gl.glShaderSource(s, src.read())
            gl.glCompileShader(s)

            result = gl.glGetShaderiv(s, gl.GL_COMPILE_STATUS)

            if not result:
                log = gl.glGetShaderInfoLog(s)

                utils.abort(f"error while compiling a shader {os.path.basename(path)}: {str(log)}")

            return s
        
        vs = load_shader(gl.GL_VERTEX_SHADER, vs_path)
        fs = load_shader(gl.GL_FRAGMENT_SHADER, fs_path)

        p = gl.glCreateProgram()

        gl.glAttachShader(p, vs)
        gl.glAttachShader(p, fs)

        gl.glLinkProgram(p)
        result = gl.glGetProgramiv(p, gl.GL_LINK_STATUS)

        if not result:
            log = gl.glGetProgramInfoLog(p)

            utils.abort(f"error while linking a ShaderPipeline with {os.path.basename(vs_path)} and {os.path.basename(fs_path)}: {log}")

        self.shader_program = p
    
        # setup uniform block bindings 

        g_loc = gl.glGetUniformBlockIndex(p, "cue_global_buf")
        if g_loc != gl.GL_INVALID_INDEX:
            gl.glUniformBlockBinding(p, g_loc, CueGLUniformBindings.GLOBAL)

        c_loc = gl.glGetUniformBlockIndex(p, "cue_camera_buf")
        if c_loc != gl.GL_INVALID_INDEX:
            gl.glUniformBlockBinding(p, c_loc, CueGLUniformBindings.CAMERA)

    def bind(self) -> None:
        gl.glUseProgram(self.shader_program)

    shader_program: gl.GLuint
