import pygame as pg
import pygame.math as pm

# == Cue entity type example implementation ==

# this is the same as `bt_example_radio.py` but implemented with a python class instead of a dict

class Radio:
    def __init__(self, pos: pm.Vector3, snd_name: str, autoplay: bool):
        self.pos = pos
        self.snd_name = snd_name

        # new radio spawned -> load the sound
    
        self.audio_channel = None
        self.audio_snd = audio.load(snd_name)
    
        if autoplay:
            self.audio_channel = audio.play(self.audio_snd, loop=1)

    def radio_spawn(pos: pm.Vector3, snd_name: str, autoplay: bool) -> dict:
        # return the entity, this will be given to us back in the other functions as an argument `e`
            
        return Radio(pos, snd_name, autoplay)

    def radio_despawn(self) -> None:
        # radio despawned -> stop sound and unload
    
        if not self.audio_channel == None:
            self.audio_channel.stop()
            self.audio_channel = None

    def radio_event(self, ev: pg.event.Event) -> bool:
        # a pygame event received, check if it's a `E` key press
    
        if ev.type == pg.KEYDOWN and ev.key == pg.K_E:
            if self.audio_channel == None:
                # start audio playback
        
                self.audio_channel = audio.play(self.audio_snd, loop=1)
                self.audio_channel = None
            else:
                # stop radio playback

                self.audio_channel.stop()
                self.audio_channel = None

        return False # do not block event for other entities (this is what you want 80% of the time)

# notify Cue that a new entity type exists
en.create_entity_type("bt_example_radio_c", Radio.radio_spawn, Radio.radio_despawn, None, Radio.radio_event)

# notify Cue that this entity type will want to be called on `event` for events of type pg.KEYDOWN
en.assign_events("bt_example_radio_c", [pg.KEYDOWN])

