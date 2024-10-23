import pygame as pg
import pygame.math as pm

import math

from ..rendering.cue_camera import Camera
from ..cue_state import GameState

from .. import cue_sequence as seq

# a simple reusable freecam / noclip camera controller
# note: this controller supports input capture / release, by default input is released and inputs will not work

class FreecamController:
    free_accel: float = 20
    free_mouse_accel: float = .2
    free_friction: float = 10

    free_vel: pm.Vector3
    free_pos: pm.Vector3
    free_rot: pm.Vector3

    controlled_camera: Camera
    is_captured: bool

    def __init__(self, cam) -> None:
        self.free_vel = pm.Vector3(0, 0, 0)
        self.free_pos = pm.Vector3(0, 0, 0)
        self.free_rot = pm.Vector3(0, 0, 0)

        self.controlled_camera = cam
        self.is_captured = False

        seq.next(self.tick)

    def tick(self) -> None:
        yaw_rot, pitch_rot = self.free_rot.yx
        yaw_rot = math.radians(yaw_rot)
        pitch_rot = math.radians(pitch_rot)

        keys = pg.key.get_pressed()
        rel = pg.mouse.get_rel()
        dt = GameState.delta_time

        self.free_vel /= 1. + (FreecamController.free_friction * dt)

        if self.is_captured:
            forward_vec = pm.Vector3(math.sin(yaw_rot) * math.cos(pitch_rot), math.sin(pitch_rot), math.cos(yaw_rot) * math.cos(pitch_rot)) * -1
            right_vec = pm.Vector3(-forward_vec.z, 0., forward_vec.x)

            if keys[pg.K_w]:
                self.free_vel += forward_vec * FreecamController.free_accel * dt
            if keys[pg.K_s]:
                self.free_vel -= forward_vec * FreecamController.free_accel * dt
            if keys[pg.K_d]:
                self.free_vel += right_vec * FreecamController.free_accel * dt
            if keys[pg.K_a]:
                self.free_vel -= right_vec * FreecamController.free_accel * dt

            self.free_rot.x += rel[1] * FreecamController.free_mouse_accel
            self.free_rot.y -= rel[0] * FreecamController.free_mouse_accel
            
            res = GameState.renderer.win_res
            pg.mouse.set_pos(res[0] // 2, res[1] // 2)

        self.free_pos += self.free_vel * dt
        self.controlled_camera.set_view(self.free_pos, self.free_rot)
        
        seq.next(FreecamController.tick, self)

    def set_capture(self, capture: bool) -> None:
        if self.is_captured == capture:
            return

        pg.event.set_grab(capture)
        pg.mouse.set_visible(not capture)

        self.is_captured = capture