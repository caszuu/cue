import os, sys, time

import pygame as pg
import numpy as np
import imgui

from ..rendering.cue_renderer import CueRenderer
from ..rendering.cue_camera import Camera
from ..rendering.cue_scene import RenderScene
from ..im2d.imgui_integ import CueImguiContext

from .. import cue_utils as utils
from ..rendering import cue_resources as res
from ..rendering import cue_batch as bat

# == On-Cue Bootstrap ==

def start_editor():
    print(f"\n[{utils.bold_escape}info{utils.reset_escape}] [bootstrap] starting the On-Cue Editor")

    # init window

    global_renderer = CueRenderer((1280, 720), vsync=False)
    pg.display.set_caption("On-Cue Editor")

    main_cam = Camera(1280 / 720)
    scene = RenderScene()

    pipeline = res.ShaderPipeline("cue/editor/fs_trig.vert", "cue/editor/menu.frag")
    mesh = res.GPUMesh(global_renderer.model_vao)
    mesh.write_to(np.array([0, 1, 0, 1, 1, 0, 1, 0, 0], dtype=np.dtypes.Float32DType), 3)

    mesh_ins = bat.MeshBatch(None, res.GPUMesh(global_renderer.model_vao), pipeline)
    mesh_ins.draw_count = 3

    scene.append(mesh_ins)

    ui_ctx = global_renderer.fullscreen_imgui_ctx

    t = time.perf_counter()

    while True:
        # == event poll ==

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
