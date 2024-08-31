import OpenGL.GL as gl

class CueEntity:
    pass

# == cue OpenGL renderer backend ==

class MeshInstance:
    __slots__ = ["mesh", "pipeline", "is_opaque", "entity"]

    # TODO: add instancing

    def __init__(self, entity: CueEntity, mesh: str, vs: str, fs: str, is_opaque: bool = True) -> None:
        self.entity = entity
        self.mesh = VertexMesh(mesh)
        self.pipeline = ShaderPipeline(vs, fs)

        self.is_opaque = is_opaque

        pass # TODO

    def draw(self) -> None:
        self.pipeline.bind()
        self.mesh.bind_and_draw()

    def order_depth(self, cam) -> float:
        x = cam.project_vec(self.entity.transform_position) - cam.cam_pos
        return np.sqrt(np.dot(x, x))

    mesh: VertexMesh
    pipeline: ShaderPipeline

    entity: CueEntity

    # entity metadata - must *never* change
    is_opaque: bool
