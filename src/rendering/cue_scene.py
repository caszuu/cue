import OpenGL.GL as gl

from cue_utils import mapped_refcount_list
from .cue_resources import ShaderPipeline
from .cue_batch import MeshBatch

# an ordered collection of rendering batches, usually represents a "scene"

class RenderScene:
    # __slots__ = []
    
    def __init__(self):
        self.attached_opaque_batches = {}
        self.attached_non_opaque_batches = {}

        self.attached_render_targets = mapped_refcount_list()

    # == batch api ==

    def append(self, batch: MeshBatch) -> None:
        if batch.is_opaque:
            attached_batches = self.attached_opaque_batches
        else:
            attached_batches = self.attached_non_opaque_batches

        scene_batch_buf = attached_batches.get(batch.draw_state, None)

        if scene_batch_buf == None:
            scene_batch_buf = { batch: None }
            attached_batches[batch.draw_state] = scene_batch_buf
            return

        # note: no KeyError raised when batch already present
        #       if two batches are hash equivalent, the override should also be equivalent
        scene_batch_buf[batch] = None

    def remove(self, batch: MeshBatch) -> None:
        if batch.is_opaque:
            attached_batches = self.attached_opaque_batches
        else:
            attached_batches = self.attached_non_opaque_batches

        scene_batch_buf = attached_batches[batch.draw_state]
        scene_batch_buf.pop(batch)

    # == frame api ==

    def try_view_deps(self) -> None:
        for target in self.attached_render_targets.list_buf:
            if target.try_view_frame(): break

    def frame(self) -> None:
        draw = MeshBatch.draw
        pipe_bind = ShaderPipeline.bind
        vao_bind = gl.glBindVertexArray

        # opaque pass

        for state, batches in self.attached_opaque_batches.items():
            vao_bind(state[0])
            pipe_bind(state[1])

            for b in batches: # dict key iter
                draw(b)

        # non-opaque pass
        # TODO: depth based ordering (?)

        for state, batches in self.attached_non_opaque_batches.items():
            vao_bind(state[0])
            pipe_bind(state[1])

            for b in batches:
                draw(b)

    # note on perf: raw dicts with raw .items() access consistently performed
    #               the best (other than list iteration, which can't be used
    #               because .index() would vastly outweigh any perf benefits)

    # also note that these batch buffers *rely* on dicts to preserve the insertion order
    # this is only guaranteed from python 3.7+

    attached_opaque_batches: dict[
        tuple[
            gl.GLuint,      # draw_vao
            ShaderPipeline, # draw_pipeline
        ],
        dict[MeshBatch] # key only
    ]

    attached_non_opaque_batches: dict[
        tuple[
            gl.GLuint,      # draw_vao
            ShaderPipeline, # draw_pipeline
        ],
        dict[MeshBatch] # key only
    ]

    attached_render_targets: mapped_refcount_list[int, int]
    
