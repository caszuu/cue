# == On-Cue Bootstrap ==

import os, sys, time
sys.path.append(os.path.dirname(__file__) + "/../src") # Cue Engine package dir

import pygame as pg
import numpy as np
import imgui

import rendering.cue_renderer as renderer
from rendering.cue_camera import Camera
from rendering.cue_scene import RenderScene
from im2d.imgui_integ import CueImguiContext

import cue_entity as entity
import cue_utils as utils
import rendering.cue_resources as res
import rendering.cue_batch as bat

print(f"\n[{utils.debug_escape}info{utils.reset_escape}] [bootstrap] starting the Cue Engine")

global_renderer = renderer.CueRenderer((1280, 720), vsync=False)
pg.display.set_caption("cue engine")

main_cam = Camera(1280 / 720)
scene = RenderScene()

pipeline = res.ShaderPipeline("on_cue/fs_trig.vert", "on_cue/menu.frag")
mesh = res.GPUMesh(global_renderer.model_vao)
mesh.write_to(np.array([0, 1, 0, 1, 1, 0, 1, 0, 0], dtype=np.dtypes.Float32DType), 3)

mesh_ins = bat.MeshBatch(None, res.GPUMesh(global_renderer.model_vao), pipeline)
mesh_ins.draw_count = 3

scene.append(mesh_ins)

ui_ctx = global_renderer.fullscreen_imgui_ctx

t = time.perf_counter()

while True:
    # == evemt poll ==

    for e in pg.event.get():
        ui_ctx.process_key_event(e)

        if e.type == pg.MOUSEMOTION:
            ui_ctx.set_mouse_input(e.pos)

        elif e.type == pg.VIDEORESIZE:
            ui_ctx.resize_display(e.size)

        elif e.type == pg.QUIT:
            exit(0) 

    # == tick ==

    dt = time.perf_counter() - t
    t = time.perf_counter()

    global_renderer.fullscreen_imgui_ctx.delta_time(dt)
    ui_ctx.delta_time(dt)

    # == frame ==
   
    ui_ctx.set_as_current_context()
    imgui.new_frame()

    imgui.show_test_window()

    global_renderer.frame(main_cam, scene)
