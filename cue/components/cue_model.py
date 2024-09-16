from .. import cue_asset as assets
from .. import cue_sequence as seq
from ..rendering import cue_scene as sc

from ..rendering.cue_batch import DrawBatch
from ..rendering.cue_resources import GPUMesh, GPUTexture, ShaderPipeline
from ..cue_state import GameState

from .cue_transform import Transform

# a generic model rendering component shared between entities

class ModelRenderer:
    def __init__(self, en_data: dict, en_trans: Transform, target_scene: 'sc.RenderScene' = GameState.active_scene) -> None:
        # load assets from preload or disk
        
        self.mesh = assets.load(en_data["a_model_mesh"])
        self.material = assets.load(en_data["a_model_material"])

        r = self
        def update_trans(trans: Transform) -> None:
            m = r
            if not m is None:
                m.model_matrix = trans._trans_matrix
                seq.on_event(trans.change_event_id, update_trans)

        self.scene = target_scene
        self.batch = DrawBatch(self.mesh, self.material.pipeline)

        self.model_transform = en_trans
        seq.on_event(self.model_transform.change_event_id, update_trans)

        # insert model into the render_scene

        self.is_visible = False
        self.show()

    # def __del__(self) -> None:
    #     pass

    # start rendering this model if hidden
    def show(self) -> None:
        if not self.is_visible:
            self.scene.append(self.batch)
            self.is_visible = True

    # stop rendering this model without deleting it (yet)
    def hide(self) -> None:
        if self.is_visible:
            self.scene.remove(self.batch)
            self.is_visible = False

    def _update_trans(trans: Transform) -> None:
        self.model_matrix = trans.trans_matrix
