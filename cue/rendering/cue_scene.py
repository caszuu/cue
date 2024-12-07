from dataclasses import dataclass
import OpenGL.GL as gl
import numpy as np

from .cue_resources import GPUTexture, ShaderPipeline
from .cue_batch import DrawBatch, DrawInstance, DrawState

# note: non-cycle-causing import only for type hints
from . import cue_target as tar

# an ordered collection of rendering batches, usually represents a "scene"

@dataclass(init=False, slots=True)
class RenderScene:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.attached_opaque_batches = {}
        self.attached_non_opaque_instances = set()
        self.non_opaque_batch_buf = {}

        self.attached_render_targets = {}

    # == batch api ==

    def append(self, ins: DrawInstance) -> None:
        if ins.is_opaque:
            scene_batches = self.attached_opaque_batches
            scene_batch_buf = scene_batches.get(ins.draw_state, None)

            if scene_batch_buf == None:
                scene_batch_buf = (DrawBatch(ins.draw_state), set())
                scene_batch_buf[1].add(ins)

                scene_batches[ins.draw_state] = scene_batch_buf
                return

            # note: no KeyError raised / no check when instance already present
            #       if two instances are hash equivalent, the override should also be equivalent
            scene_batch_buf[1].add(ins)
        else:
            scene_batches = self.non_opaque_batch_buf
            scene_batch = scene_batches.get(ins.draw_state, None)

            if scene_batch == None:
                scene_batch = DrawBatch(ins.draw_state)
                scene_batches[ins.draw_state] = scene_batch

            self.attached_non_opaque_instances.add(ins)

    def remove(self, ins: DrawInstance) -> None:
        if ins.is_opaque:
            scene_batches = self.attached_opaque_batches

            scene_batch_buf = scene_batches[ins.draw_state]
            scene_batch_buf[1].remove(ins)

            if not scene_batch_buf[1]:
                scene_batches.pop(ins.draw_state)
        else:
            self.attached_non_opaque_instances.remove(ins)

            scene_batches = self.non_opaque_batch_buf
            scene_batch = scene_batches[ins.draw_state]

            # FIXME: remove batch when not in use
            # if not scene_batch:
            #     scene_batches.pop(ins.draw_state)

    # == frame api ==

    def try_view_deps(self) -> None:
        for target in self.attached_render_targets:
            target.try_view_frame()

    def frame(self, cam_mat: np.ndarray) -> None:
        pipe_bind = ShaderPipeline.bind
        bind_tex = GPUTexture.bind_to

        draw_instance = DrawBatch.draw_instance
        draw_batch = DrawBatch.draw_batch
        draw_append = DrawBatch.append_instance

        def process_batch(state, batch, ins_buf):
            pipe_bind(state.draw_pipeline)

            for i, tex in enumerate(state.draw_texture_binds):
                bind_tex(tex, i)

            if len(ins_buf) == 1:
                draw_instance(batch, *ins_buf) # only a single instance, do a normal draw call
                return
            
            # batch draw instances into instanced draw calls
            for ins in ins_buf:
                draw_append(batch, ins)
            draw_batch(batch)

        # opaque pass

        # PERF TODO: not rebind pipeline / vao for multiple different texture binds
        #            not sure how much it would improve perf / how common different skins are

        gl.glDisable(gl.GL_BLEND)

        for state, instances in self.attached_opaque_batches.items():
            process_batch(state, *instances)

        # non-opaque pass

        view_dist = DrawInstance.view_depth
        non_opaque_batches = self.non_opaque_batch_buf

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        # order non-opaque instances based on depth from viewing point
        view_ordered_ins = sorted(self.attached_non_opaque_instances, key=lambda ins: view_dist(ins, cam_mat), reverse=True)

        batch_state = None
        batched_ins = []

        for ins in view_ordered_ins:
            state = ins.draw_state

            # check if can be batched
            if batch_state == state:
                batched_ins.append(ins)
                continue

            elif batch_state is not None:
                # submit previous incompatible batch
                process_batch(batch_state, non_opaque_batches[batch_state], batched_ins)

            # setup new batch
            batch_state = state
            batched_ins = [ins]
        
        # submit last batch
        if batch_state is not None:
            process_batch(batch_state, non_opaque_batches[batch_state], batched_ins)

    # note on perf: raw dicts with raw .items() access consistently performed
    #               the best (other than list iteration, which can't be used
    #               because .index() would vastly outweigh any perf benefits)

    # fully unordered, merge-able batches into instance batches
    attached_opaque_batches: dict[
        DrawState,
        tuple[DrawBatch, set[DrawInstance]]
    ]

    # ordered (every frame) on view dist, very limited batch merging (due to rasterization order)
    attached_non_opaque_instances: set[DrawInstance]
    non_opaque_batch_buf: dict[DrawState, DrawBatch]

    attached_render_targets: dict['tar.RenderTarget', int] # key: render target, value: ref count
    
