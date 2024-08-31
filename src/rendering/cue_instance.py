import OpenGL.GL as gl
from .cue_resources import GPUMesh, ShaderPipeline

class CueEntity:
    pass

# == cue rendering instances ==

# rendering instances contain semi-local runtime buffers
# for each object being instanced (mesh, point, etc.)

class MeshInstance:
    __slots__ = ["mesh", "pipeline", "is_opaque", "entity"]

    # TODO: add instancing

    def __init__(self, entity: CueEntity, mesh: GPUMesh, pipeline: ShaderPipeline, is_opaque: bool = True) -> None:
        self.entity = entity
        self.mesh = mesh
        self.pipeline = pipeline

        self.is_opaque = is_opaque

        # TODO: create instancing device buffers

    def draw(self) -> None:
        gl.glDrawElements(gl.GL_TRIANGLES, self.vertex_count, gl.GL_UNSIGNED_INT, 0)

    mesh: GPUMesh
    pipeline: ShaderPipeline

    entity: CueEntity

    # entity metadata - must *never* change
    is_opaque: bool
