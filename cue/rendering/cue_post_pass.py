from dataclasses import dataclass
import OpenGL.GL as gl
import numpy as np

from ..cue_state import GameState
from .. import cue_utils as utils

from .cue_framebuffer import RenderAttachment, RenderFramebuffer
from .cue_resources import ShaderPipeline

# few basic implementations of port-processing passes

@dataclass(init=False, slots=True)
class PostPass:
    def dispatch(self, src: RenderFramebuffer, dst_fb: np.uint32) -> None:
        raise NotImplemented

    def resize(self, size: tuple[int, int]) -> None:
        pass

# a basic single-pass post pass base

@dataclass(init=False, slots=True)
class SinglePassPostPass(PostPass):
    def __init__(self, pipeline: ShaderPipeline) -> None:
        self.pass_pipe = pipeline

    # setup your ogl state and uniforms here
    def setup_dispatch(self, src: RenderFramebuffer, dst_fb: np.uint32) -> None:
        pass

    def dispatch(self, src: RenderFramebuffer, dst_fb: np.uint32) -> None:
        self.pass_pipe.bind()
        src.fb_attachments[gl.GL_COLOR_ATTACHMENT0].bind_to(0)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, dst_fb)

        self.setup_dispatch(src, dst_fb)

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)

    def resize(self, size: tuple[int, int]) -> None:
        pass

# a basic blit pass mostly for testing

class BlitPostPass(SinglePassPostPass):
    def __init__(self) -> None:
        pipeline = GameState.asset_manager.load_shader("shaders/post/fs_trig.vert", "shaders/post/blit.frag")
        super().__init__(pipeline)