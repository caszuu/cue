# == On-Cue Bootstrap ==

import os, sys, time
sys.path.append(os.path.dirname(__file__) + "/src")

import pygame as pg
import imgui

# import rendering.cue_resources as resources
import rendering.cue_renderer as renderer
import rendering.cue_camera as cam
from im2d.imgui_integ import CueImguiContext

import cue_entity as entity
# import cue_im2d as im2d

global_renderer = renderer.CueRenderer((1280, 720), vsync=False)
pg.display.set_caption("cue engine")

ui_ctx = global_renderer.fullscreen_imgui_ctx
ui_ctx.set_as_current_context()

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
   
    ui_ctx.delta_time(dt)

    imgui.new_frame()
    imgui.show_test_window()

    global_renderer.frame(cam.Camera())
