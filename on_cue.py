# == On-Cue Bootstrap ==

import os, sys, time
sys.path.append(os.path.dirname(__file__) + "/src")

import pygame as pg
import imgui

# import rendering.cue_resources as resources
import rendering.cue_renderer as renderer
import rendering.cue_camera as cam
from im2d.imgui_integ import CueImguiContext
from rendering.cue_resources import ShaderPipeline

import cue_entity as entity
import cue_utils as utils
# import cue_im2d as im2d

print(f"\n[{utils.debug_escape}info{utils.reset_escape}] [bootstrap] starting the Cue Engine")

global_renderer = renderer.CueRenderer((1280, 720), vsync=False)
pg.display.set_caption("cue engine")

main_cam = cam.Camera()

ui_ctx = global_renderer.fullscreen_imgui_ctx

t = time.perf_counter()

while True:    
    for e in pg.event.get():
        ui_ctx.process_key_event(e)

        if e.type == pg.MOUSEMOTION:
            ui_ctx.set_mouse_input(e.pos)

        elif e.type == pg.VIDEORESIZE:
            ui_ctx.resize_display(e.size)

        elif e.type == pg.QUIT:
            exit(0) 

    dt = time.perf_counter() - t
    t = time.perf_counter()

    global_renderer.fullscreen_imgui_ctx.delta_time(dt)
    ui_ctx.delta_time(dt)

    global_renderer.fullscreen_imgui_ctx.set_as_current_context()
    imgui.new_frame()
    
    ui_ctx.set_as_current_context()
    # imgui.new_frame()
    imgui.show_test_window()

    global_renderer.frame(main_cam)
