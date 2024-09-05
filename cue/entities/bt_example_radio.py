import pygame as pg
import pygame.math as pm

import .cue_entity_types as en

# == Cue entity type example implementation ==

# the following implements a very simple entity type, it's a radio which you can turn on and off
# using the `E` key, it loads its assets in `spawn` and optionally starts auto playing on loop

# then in `event` we check if the `E` key has been pressed and toggle the radio if needed

# note: this implementation is very simple and does not do *any* rendering what so ever
#       see `bt_static_mesh.py` for a simple entity type which renders a model using a MeshRenderer

def radio_spawn(pos: pm.Vector3, snd_name: str, autoplay: bool) -> dict:
    # new radio spawned -> load the sound
    
    channel = None
    snd = audio.load(snd_name)
    
    if autoplay:
        channel = audio.play(snd, loop=1)

    # return the entity, this will be given to us back in the other functions as an argument `e`
    
    return {"pos": pos, "audio_snd": snd, "audio_channel": channel}

def radio_despawn(e: dict) -> None:
    # radio despawned -> stop sound and unload
    
    if not e["audio_channel"] == None:
        e["audio_channel"].stop()
        e["audio_channel"] = None

def radio_event(e: dict, ev: pg.event.Event) -> bool:
    # a pygame event received, check if it's a `E` key press
    
    if ev.type == pg.KEYDOWN and ev.key == pg.K_E:
        if e["audio_channel"] == None:
            # start audio playback
        
            e["audio_channel"] = audio.play(e["audio_snd"], loop=1)
            e["audio_channel"] = None
        else:
            # stop radio playback

            e["audio_channel"].stop()
            e["audio_channel"] = None

    return False # do not block event for other entities (this is what you want 80% of the time)

# notify Cue that a new entity type exists
en.create_entity_type("bt_example_radio", radio_spawn, radio_despawn, None, radio_event)

# notify Cue that this entity type will want to be called on `event` for events of type pg.KEYDOWN
en.assign_events("bt_example_radio", [pg.KEYDOWN])
