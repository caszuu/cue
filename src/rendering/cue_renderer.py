import pygame as pg
import OpenGL.GL as gl

import imgui
from imgui.integrations.pygame import PygameRenderer

from rendering.cue_camera import Camera
from src.im2d.imgui_integ import CueImguiContext

# == cue OpenGL renderer backend ==

class PostPass:
    __slots__ = []

    def dispatch(self) -> None:
        raise NotImplemented

    def recreate(self) -> None:
        pass

# == top-level renderer implemetation ==

class CueRenderer:
    __slots__ = ["win_surf", "win_res", "post_passes", "fullscreen_imgui_ctx"]

    def __init__(self, res: tuple[int, int] = (0, 0), fullscreen: bool = False, vsync: bool = True) -> None:
        pg.init()

        # if res == (0, 0):
        #     res = pg.display.get_desktop_sizes()[0]

        self.win_surf = pg.display.set_mode(res, pg.OPENGL | pg.DOUBLEBUF | pg.RESIZABLE, vsync=vsync)

        if fullscreen:
            pg.display.toggle_fullscreen()
        
        self.win_res = self.win_surf.get_size()
        self.fullscreen_imgui_ctx = CueImguiContext(self.win_res)

        self.post_passes = []

    # == post processing api ==

    def activate_post_pass(self, p: PostPass) -> None:
        self.post_passes.append(p)

    def deactivate_post_pass(self, p: PostPass) -> None:
        self.post_passes.remove(p)

    # == renderer api ==

    def frame(self, cam: Camera) -> None:
        # cam stack draw

        cam.view_frame(fb=0)

        # post-process

        for p in self.post_passes:
            p.dispatch()

        self.fullscreen_imgui_ctx.set_as_current_context()

        imgui.render()
        self.fullscreen_imgui_ctx.render(imgui.get_draw_data())

        pg.display.flip()

    # OpenGL mode pygame surface
    win_surf: pg.Surface
    win_res: tuple[int, int]

    global_vao: gl.GLuint
    fullscreen_imgui_ctx: CueImguiContext

    post_passes: list[PostPass]
