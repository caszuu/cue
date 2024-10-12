from dataclasses import dataclass
from typing import Any, Callable

import imgui
from .imgui_integ import CueImguiContext

from ..rendering.cue_resources import GPUTexture 
from pygame.math import Vector3 as Vec3, Vector2 as Vec2

# Im2D - A small wrapper over imgui draw list api with better integration with Cue
# note: Im2D does not require for the context being drawn to to be current

@dataclass(init=False, slots=True)
class Im2DContext:
    def __init__(self, imgui_context: CueImguiContext) -> None:

        last_ctx = imgui.get_current_context()

        self._imgui_ctx = imgui_context
        self._imgui_ctx.set_as_current_context()
        self._bg_dlist = imgui.get_background_draw_list()

        imgui.set_current_context(last_ctx)

    def get_display_size(self) -> tuple[int, int]:
        return self._imgui_ctx.io.display_size

    # == imgui DrawList wrapper defs ==
    
    def add_line(self, start_x: float, start_y: float, end_x: float, end_y: float, col, thickness: float = 1.0) -> None:
        self._bg_dlist.add_line(start_x, start_y, end_x, end_y, col, thickness)

    # rect

    def add_rect(self, upper_left_x: float, upper_left_y: float, lower_right_x: float, lower_right_y: float, col: int, rounding: float = 0.0, flags: int = 0, thickness: float = 1.0) -> None:
        self._bg_dlist.add_rect(upper_left_x, upper_left_y, lower_right_x, lower_right_y, col, rounding, flags, thickness)
    
    def add_rect_filled(self, upper_left_x: float, upper_left_y: float, lower_right_x: float, lower_right_y: float, col: int, rounding: float = 0.0, flags: int = 0) -> None:
        self._bg_dlist.add_rect_filled(upper_left_x, upper_left_y, lower_right_x, lower_right_y, col, rounding, flags)
    
    def add_rect_filled_multicolor(self, upper_left_x: float, upper_left_y: float, lower_right_x: float, lower_right_y: float, col_upr_left: int, col_upr_right: int, col_bot_right: int, col_bot_left: int) -> None:
        self._bg_dlist.add_rect_filled_multicolor(upper_left_x, upper_left_y, lower_right_x, lower_right_y, col_upr_left, col_upr_right, col_bot_right, col_bot_left)
    
    # quad

    def add_quad(self, 
        point1_x: float, point1_y: float,
        point2_x: float, point2_y: float,
        point3_x: float, point3_y: float,
        point4_x: float, point4_y: float,
        col: int, # cimgui.ImU32
        thickness: float = 1.0) -> None:
        self._bg_dlist.add_quad(
            point1_x, point1_y,
            point2_x, point2_y,
            point3_x, point3_y,
            point4_x, point4_y,
            col, thickness)
    
    def add_quad_filled(self, 
        point1_x: float, point1_y: float,
        point2_x: float, point2_y: float,
        point3_x: float, point3_y: float,
        point4_x: float, point4_y: float,
        col: int # cimgui.ImU32
        ) -> None:
        self._bg_dlist.add_quad_filled(
            point1_x, point1_y,
            point2_x, point2_y,
            point3_x, point3_y,
            point4_x, point4_y,
            col)
    
    # trig

    def add_triangle(self, 
        point1_x: float, point1_y: float,
        point2_x: float, point2_y: float,
        point3_x: float, point3_y: float,
        col: int, # cimgui.ImU32
        thickness: float = 1.0) -> None:
        self._bg_dlist.add_triangle(
            point1_x, point1_y,
            point2_x, point2_y,
            point3_x, point3_y,
            col, thickness)
    
    def add_triangle_filled(self, 
        point1_x: float, point1_y: float,
        point2_x: float, point2_y: float,
        point3_x: float, point3_y: float,
        col: int # cimgui.ImU32
        ) -> None:
        self._bg_dlist.add_triangle_filled(
            point1_x, point1_y,
            point2_x, point2_y,
            point3_x, point3_y,
            col)

    # bezier curves

    def add_bezier_cubic(self,
        point1_x: float, point1_y: float,
        point2_x: float, point2_y: float,
        point3_x: float, point3_y: float,
        point4_x: float, point4_y: float,
        col: int, # cimgui.ImU32
        thickness: float,
        num_segments: int = 0) -> None:
        self._bg_dlist.add_bezier_cubic(
            point1_x, point1_y,
            point2_x, point2_y,
            point3_x, point3_y,
            point4_x, point4_y,
            col, thickness, num_segments)

    def add_bezier_quadratic(self,
        point1_x: float, point1_y: float,
        point2_x: float, point2_y: float,
        point3_x: float, point3_y: float,
        col: int, # cimgui.ImU32
        thickness: float,
        num_segments: int = 0) -> None:
        self._bg_dlist.add_bezier_quadratic(
            point1_x, point1_y,
            point2_x, point2_y,
            point3_x, point3_y,
            col, thickness, num_segments)

    # circle

    def add_circle(self,
        centre_x: float, centre_y: float,
        radius: float,
        col: int, # cimgui.ImU32
        num_segments: int = 0,
        thickness: float = 1.0) -> None:
        self._bg_dlist.add_circle(
            centre_x, centre_y,
            radius, col, num_segments, thickness)

    def add_circle_filled(self,
        centre_x: float, centre_y: float,
        radius: float,
        col: int, # cimgui.ImU32
        num_segments: int = 0) -> None:
        self._bg_dlist.add_circle_filled(
            centre_x, centre_y,
            radius, col, num_segments)
        
    # ngons

    def add_ngon(self,
        centre_x: float, centre_y: float,
        radius: float,
        col: int, # cimgui.ImU32
        num_segments: int = 0,
        thickness: float = 1.0) -> None:
        self._bg_dlist.add_ngon(
            centre_x, centre_y,
            radius, col, num_segments, thickness)

    def add_ngon_filled(self,
        centre_x: float, centre_y: float,
        radius: float,
        col: int, # cimgui.ImU32
        num_segments: int = 0) -> None:
        self._bg_dlist.add_ngon_filled(
            centre_x, centre_y,
            radius, col, num_segments)    

    # text

    def add_text(self,
        pos_x: float, pos_y: float,
        col: int, # cimgui.ImU32
        text: str) -> None:
        self._bg_dlist.add_text(
            pos_x, pos_y,
            col, text)

    # image

    def add_image(self,
        texture: GPUTexture,
        a: tuple[float, float] | Vec2,
        b: tuple[float, float] | Vec2,
        uv_a: tuple[float, float] | Vec2 = (0., 0.),
        uv_b: tuple[float, float] | Vec2 = (1., 1.),
        col: int = 0xffffffff, # cimgui.ImU32
        ) -> None:
        self._bg_dlist.add_image(
            texture.texture_handle,
            a, b,
            uv_a, uv_b,
            col)
    
    def add_image_rounded(self,
        texture: GPUTexture,
        a: tuple[float, float] | Vec2,
        b: tuple[float, float] | Vec2,
        uv_a: tuple[float, float] | Vec2 = (0., 0.),
        uv_b: tuple[float, float] | Vec2 = (1., 1.),
        col: int = 0xffffffff, # cimgui.ImU32
        rounding: float = 1.0,
        flags: int = 0) -> None:
        self._bg_dlist.add_image(
            texture.texture_handle,
            a, b,
            uv_a, uv_b,
            col, rounding, flags)

    # polyline

    def add_polyline(self,
        points: list[tuple[float, float] | Vec2],
        col: int, # cimgui.ImU32
        flags: int = 0,
        thickness: float = 1.0) -> None:
        self._bg_dlist.add_polyline(
            points, col, flags, thickness)

    # TODO: paths, prims
    
    # ==

    _imgui_ctx: CueImguiContext
    _bg_dlist: imgui.core._DrawList