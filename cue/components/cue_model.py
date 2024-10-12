from .. import cue_sequence as seq
from ..rendering import cue_scene as sc

from ..rendering.cue_batch import DrawBatch
from ..rendering.cue_resources import GPUMesh, GPUTexture, ShaderPipeline
from ..cue_state import GameState

from .cue_transform import Transform

# a generic model rendering component shared between entities

class ModelRenderer:
    def __init__(self, en_data: dict, en_trans: Transform, target_scene: 'sc.RenderScene | None' = None) -> None:
        # load assets from preload or disk
        
        self.mesh = GameState.asset_manager.load_mesh(en_data["a_model_mesh"])
        self.pipeline = GameState.asset_manager.load_shader(en_data["a_model_vshader"], en_data["a_model_fshader"])

        if target_scene is None:
            target_scene = GameState.active_scene

        self.scene = target_scene
        self.batch = DrawBatch(self.mesh, self.pipeline, en_trans)

        self.model_transform = en_trans

        # insert model into the render_scene

        self.is_visible = False
        self.show()

    def __del__(self) -> None:
        if self.is_visible:
            self.hide()

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
