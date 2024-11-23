from dataclasses import dataclass
import OpenGL.GL as gl
import numpy as np

from .cue_resources import GPUTexture

# note: non-cycle-causing import only for type hints
from . import cue_camera as cam, cue_scene as sc

# an off-screen framebuffer that a Camera can render into, later can be used as a texture in the scene

@dataclass(init=False, slots=True)
class RenderTarget:
    def __init__(self, size: tuple[int, int], attachments: list[tuple[np.uint32, np.uint32, np.uint32, np.uint32]]) -> None:
        self.target_fb = gl.glGenFramebuffers(1)
        self.target_attachments = []

        target_attachments = self.target_attachments
        tex_init = GPUTexture.init_null

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.target_fb)
        
        for i in range(len(attachments)):
            tex = GPUTexture()
            tex_init(tex, size, attachments[i][2], attachments[i][3], attachments[i][1])            
            
            gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, attachments[i][0], gl.GL_TEXTURE_2D, tex.texture_handle, 0)
            target_attachments.append(tex)

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def try_view_frame(self) -> None:
        self.current_state = 0

        if self.current_state == 0:
            # not yet rendered, view_frame target

            self.current_state = 1
            self.target_camera.view_frame(self.target_fb, self.target_scene)
            self.current_state = 3

        elif self.current_state == 1:
            # recursive RenderScenes, clear fb and stop recursion
            # TODO: might allow x-number of recursions (for Portal like effect)
            #       might allow special draws on recursion limit

            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.target_fb)

            gl.glClearColor(0., 0., 0., 1.)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)

            self.current_state = 2
            
        elif self.current_state == 2:
            pass # already clear

        else:
            pass # already rendered

    # 0 - try_view_frame not called
    # 1 - try_view_frame in-progress (might encounter in a recursive scene)
    # 2 - try_view_frame in-proggres + already recursed
    # 3 - try_view_frame finished
    current_state: int

    target_fb: np.uint32
    target_attachments: list[GPUTexture]

    target_camera: 'cam.Camera'
    target_scene: 'sc.RenderScene'
