import sys
from dataclasses import dataclass

import OpenGL.GL as gl
import numpy as np

from .cue_resources import GPUTexture

# an off-screen framebuffer that a Camera can render into, later can be used as a texture in the scene

@dataclass(slots=True)
class RenderAttachment:
    attachment_enum: np.uint32

    tex_type: np.uint32 = np.uint32(0)
    tex_format: np.uint32 = np.uint32(0)
    tex_internalformat: np.uint32 | None = None # if None, tex_format will be used for internalformat

    external_tex: GPUTexture | None = None # if not Note, all tex_* params are ignored, no internal texture is allocated and this texture is bound as the attachment

@dataclass(init=False, slots=True)
class RenderFramebuffer:
    def __init__(self, size: tuple[int, int], attachments: list[RenderAttachment]) -> None:
        self.fb_handle = gl.glGenFramebuffers(1)
        self.fb_attachments = {}

        fb_attachments = self.fb_attachments
        tex_init = GPUTexture.init_null

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fb_handle)
        
        for i in range(len(attachments)):
            tex = attachments[i].external_tex
            if tex is None:
                tex = GPUTexture()
                tex_init(tex, size, attachments[i].tex_format, attachments[i].tex_type, attachments[i].tex_internalformat)            

            gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, attachments[i].attachment_enum, gl.GL_TEXTURE_2D, tex.texture_handle, 0)
            fb_attachments[attachments[i].attachment_enum] = tex

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def __del__(self) -> None:
        if sys.meta_path is None: # python is likely shuting down, pyopengl will fail, just let the resources get freed by the os
            return

        gl.glDeleteFramebuffers(1, [self.fb_handle])

    fb_handle: np.uint32
    fb_attachments: dict[np.uint32, GPUTexture] # dict[attachment_enum, attachment_texture]
