import OpenGL.GL as gl

from .cue_camera import Camera
from .cue_scene import RenderScene
from .cue_resources import GPUTexture

# an off-screen framebuffer that a Camera can render into, later can be used as a texture in the scene

class RenderTarget:
    __slots__ = []

    def __init__(self, size: tuple[int, int], attachments: list[tuple[gl.GLuint, gl.GLuint, gl.GLuint]]) -> None:
        self.target_fb = gl.glGenFramebuffers(1)
        self.target_attachments = []

        target_attachments = self.target_attachments
        tex_init = GPUTexture.init_null
        
        for i in range(len(attachments)):
            tex = GPUTexture()
            tex_init(tex, size, attachments[i][1], attachments[i][2])            
            
            gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, attachments[i][0], gl.GL_TEXTURE_2D, tex.texture_handle, 0)
            target_attachments.append(tex)

    def __del__(self) -> None:
        gl.glDeleteFramebuffers(1, [self.target_fb])

        # attachment data might still be in use, leave it at the gc
        #
        # for attach in self.target_attachments:
        #     del attach

    def try_view_frame(self) -> None:
        if self.current_state == 0:
            # not yet rendered, view_frame target

            self.current_state = 1
            self.target_camera.view_frame(self.target_fb, self.target_scene)
            self.current_state = 3

        elif self.current_state == 1:
            # recursive RenderScenes, clear fb and stop recursion
            # TODO: might allow x-number of recursions (for Portal like effect)
            #       might allow special draws on recursion limit

            gl.glBindFramebuffer(self.target_fb)

            gl.glClearColor(0., 0., 0., 1.)
            gl.glClear(gl.GL_COLOR_ATTACHMENT)

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

    target_fb: gl.GLuint
    target_attachments: list[GPUTexture]

    target_camera: Camera
    target_scene: RenderScene
