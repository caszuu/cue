from .rendering import cue_renderer as ren, cue_scene as ren_sc, cue_camera as ren_cam
from . import cue_sequence as seq, cue_entity_storage as en#, cue_asset_manager as ast

# == Cue Game State ==

# This is a top-levl global class containing refs to the many storage classes
# currently in use by the engine code

class GameState:
    # == subsystem handles ==

    renderer: 'ren.CueRenderer'

    sequencer: 'seq.CueSequencer'
    entity_storage: 'en.EntityStorage'
    asset_manager: 'en.AssetManager'

    # == main binding states ==

    active_scene: 'ren_sc.RenderScene'
    active_camera: 'ren_cam.Camera'

    # == global vars ==

    delta_time: float
    
    cpu_tick_time: float
    cpu_render_time: float
