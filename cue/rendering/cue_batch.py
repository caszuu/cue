import OpenGL.GL as gl
from .cue_resources import GPUMesh, ShaderPipeline

# == cue rendering instances ==

# rendering batch contain semi-local runtime buffers
# for each object being instanced (mesh, point, etc.)

class MeshBatch:
    __slots__ = ["mesh", "pipeline", "is_opaque", "draw_state", "has_elements", "draw_count"]

    # TODO: add instancing

    def __init__(self, mesh: GPUMesh, pipeline: ShaderPipeline, is_opaque: bool = True) -> None:
        self.mesh = mesh
        self.pipeline = pipeline
        self.draw_state = (mesh.mesh_vao, pipeline)

        self.is_opaque = is_opaque

        self.has_elements = mesh.mesh_ebo != -1
        self.draw_count = mesh.element_count if self.has_elements else mesh.vertex_count

    def draw(self) -> None:
        if self.has_elements:
            gl.glDrawElements(gl.GL_TRIANGLES, self.draw_count, gl.GL_UNSIGNED_INT, 0)
            return

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, self.draw_count)

    mesh: GPUMesh
    pipeline: ShaderPipeline

    # required by RenderScene for sorting
    draw_state: tuple[gl.GLuint, ShaderPipeline]

    # entity metadata - must *never* change
    is_opaque: bool

    # draw_count will mostly be the same as mesh.vertex_count, but can differ (eg. with vertex shaders generation their own data)
    draw_count: gl.GLuint
    has_elements: bool
