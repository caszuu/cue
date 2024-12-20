from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # the following imports technically cause a cyclic import, but they're only used for
    # type hints, to it's hidden behind a `TYPE_CHECKING` if and never imported while actually running

    from .rendering import cue_renderer as ren, cue_scene as ren_sc, cue_camera as ren_cam
    from . import cue_sequence as seq, cue_entity_storage as en, cue_assets as ast
    from .phys import cue_phys_scene as phys

# == Cue Game State ==

# This is a top-levl global class containing refs to the many engine system classes

class GameState:
    # == subsystem handles ==

    renderer: 'ren.CueRenderer'

    sequencer: 'seq.CueSequencer'
    static_sequencer: 'seq.CueSequencer'
    entity_storage: 'en.EntityStorage'
    asset_manager: 'ast.AssetManager'

    # == main binding states ==

    active_scene: 'ren_sc.RenderScene'
    active_camera: 'ren_cam.Camera'

    collider_scene: 'phys.PhysScene'
    trigger_scene: 'phys.PhysScene'

    # == global vars ==

    delta_time: float
    current_time: float
    
    cpu_tick_time: float
    cpu_render_time: float

    current_map: str
    next_map_deferred: str
