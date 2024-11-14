from typing import Any
import ctypes
import os

from pygame.math import Vector3 as Vec3, Vector2 as Vec2
import numpy as np

import OpenGL.GL as gl
import imgui

from ..cue_state import GameState
from .cue_resources import ShaderPipeline

# == Simple Debug Gizmo Draw Api ==

# this implmenetation is very srappy as it's intended to only be used for debug
# it can be used anywhere and the drawn gizmos will persist only for a frame

class CueGizmos:
    draw_stack: list[tuple] = []
    draw_stack_byte_size = 0

    draw_buffer: np.uint32
    draw_vao: np.uint32

    draw_shader: ShaderPipeline

# size is: float32 size == 4, 3 floats per vec, 2 vecs per vert
GIZMO_VERT_SIZE = np.dtype('float32').itemsize * 3 * 2

# == gizmo api ==

def draw_line(pos1: Vec3, pos2: Vec3, col1: Vec3 = Vec3(1, 1, 1), col2: Vec3 = Vec3(1, 1, 1)) -> None:
    CueGizmos.draw_stack.append((0, np.array([*pos1, *col1, *pos2, *col2], dtype=np.float32)))
    CueGizmos.draw_stack_byte_size += GIZMO_VERT_SIZE * 2

def draw_box(min_p: Vec3, max_p: Vec3, line_col: Vec3) -> None:
    # min x edges
    draw_line(min_p, Vec3(min_p.x, min_p.y, max_p.z), line_col, line_col)
    draw_line(Vec3(min_p.x, min_p.y, max_p.z), Vec3(min_p.x, max_p.y, max_p.z), line_col, line_col)
    draw_line(Vec3(min_p.x, max_p.y, max_p.z), Vec3(min_p.x, max_p.y, min_p.z), line_col, line_col)
    draw_line(Vec3(min_p.x, max_p.y, min_p.z), min_p, line_col, line_col)

    # max x edges
    draw_line(Vec3(max_p.x, min_p.y, min_p.z), Vec3(max_p.x, min_p.y, max_p.z), line_col, line_col)
    draw_line(Vec3(max_p.x, min_p.y, max_p.z), Vec3(max_p.x, max_p.y, max_p.z), line_col, line_col)
    draw_line(Vec3(max_p.x, max_p.y, max_p.z), Vec3(max_p.x, max_p.y, min_p.z), line_col, line_col)
    draw_line(Vec3(max_p.x, max_p.y, min_p.z), Vec3(max_p.x, min_p.y, min_p.z), line_col, line_col)

    # rest
    draw_line(Vec3(min_p.x, min_p.y, min_p.z), Vec3(max_p.x, min_p.y, min_p.z), line_col, line_col)
    draw_line(Vec3(min_p.x, max_p.y, min_p.z), Vec3(max_p.x, max_p.y, min_p.z), line_col, line_col)
    draw_line(Vec3(min_p.x, min_p.y, max_p.z), Vec3(max_p.x, min_p.y, max_p.z), line_col, line_col)
    draw_line(Vec3(min_p.x, max_p.y, max_p.z), Vec3(max_p.x, max_p.y, max_p.z), line_col, line_col)

@np.errstate(all='ignore')
def draw_text(pos: Vec3, text: str, col: Vec3 = Vec3(1., 1., 1.), start_fade: float = 4., end_fade: float = 4.5) -> None:
    # text is implemented with imgui

    # calculate screen space pos for point (camera matrix and prespective divide)
    x, y, z, w = (GameState.active_camera.cam_view_proj_matrix @ np.array((*pos, 1.), dtype=np.float32))
    x /= w
    y /= w
    z /= w
    
    if z < 0. or z > 1.:
        return

    world_dist = (GameState.active_camera.cam_pos - pos).length_squared()
    alpha = 1. - min(max((world_dist - start_fade) / end_fade, 0.), 1.)

    # scale down to 0 to 1 range (and flip y for imgui)
    x = x * .5 + .5
    y = -y * .5 + .5

    x_res, y_res = GameState.renderer.win_res
    imgui.get_background_draw_list().add_text(x * x_res, y * y_res, imgui.get_color_u32_rgba(*col, alpha), text)

# TODO: more gizmos if required

# == submit api ==

def init_gizmos() -> None:
    CueGizmos.draw_vao = gl.glGenVertexArrays(1)
    gl.glBindVertexArray(CueGizmos.draw_vao)

    CueGizmos.draw_buffer = gl.glGenBuffers(1)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, CueGizmos.draw_buffer)

    gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, False, 6 * 4, None)
    gl.glEnableVertexAttribArray(0)

    gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, False, 6 * 4, ctypes.c_void_p(3 * 4))
    gl.glEnableVertexAttribArray(1)

    CueGizmos.draw_shader = ShaderPipeline(open(os.path.dirname(__file__) + "/gizmo_draw.vert", 'r').read(), open(os.path.dirname(__file__) + "/gizmo_draw.frag", 'r').read(), "gizmo_draw")

def draw_gizmos() -> None:
    if not CueGizmos.draw_stack:
        return # early-out if gizmos are not in use
    
    # reset draw_buffer
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, CueGizmos.draw_buffer)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, CueGizmos.draw_stack_byte_size, None, gl.GL_STREAM_DRAW)

    gl.glBindVertexArray(CueGizmos.draw_vao)
    gl.glUseProgram(CueGizmos.draw_shader.shader_program)

    # gizmos overdraw everything
    gl.glDisable(gl.GL_DEPTH_TEST)

    vert_head = 0
    for draw in CueGizmos.draw_stack:
        gl.glBufferSubData(gl.GL_ARRAY_BUFFER, GIZMO_VERT_SIZE * vert_head, draw[1])

        if draw[0] == 0: # draw_line
            gl.glDrawArrays(gl.GL_LINES, vert_head, 2)
            vert_head += 2

        # elif draw[0] == 1:

    # reset
    CueGizmos.draw_stack.clear()
    CueGizmos.draw_stack_byte_size = 0