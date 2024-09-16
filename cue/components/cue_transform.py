import pygame.math as pm
from typing import Callable

from .. import cue_utils as utils
from .. import cue_sequence as seq

import numpy as np

# a generic object transform (pos, rot and scale) implementation shared between entities

class Transform:
    def __init__(self, pos: pm.Vector3, rot: pm.Vector3, scale: pm.Vector3 = pm.Vector3(1., 1., 1.)) -> None:
        self._pos = pos
        self._rot = rot
        self._scale = scale

        self._change_event = seq.create_event("trans_change")
        self._update()

    # == transform api ==

    def set_pos(self, pos: pm.Vector3) -> None:
        self._pos = pos
        self._update()

    def set_rot(self, rot: pm.Vector3) -> None:
        self._rot = rot
        self._update()

    def set_scale(self, scale: pm.Vector3) -> None:
        self._scale = scale
        self._update()

    def _update(self) -> None:
        self._trans_matrix = (
            utils.mat4_scale(self._scale) @
            utils.mat4_rotate(self._rot.x, (1., 0., 0.)) @
            utils.mat4_rotate(self._rot.y, (0., -1., 0.)) @
            utils.mat4_rotate(self._rot.z, (0., 0., 1.)) @
            utils.mat4_translate(self._pos)
        )

        seq.fire_event(self._change_event, self)

    # do *not* change directly, use set_* to set entries
    _pos: pm.Vector3
    _rot: pm.Vector3
    _scale: pm.Vector3

    _change_event: int
