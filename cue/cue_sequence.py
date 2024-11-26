from typing import Callable, Any
from bisect import bisect_left, bisect_right

import time
import pygame as pg

# == Cue Sequences and Sequencer ==

# Cue sequences are the primary way of scripting in Cue, they are essentially simplified coroutines or async
# with explicit yielding / returning. 
#
# They work by a way of a constantly refreshing event loop. At any time you can call eg. `seq.next(my_func)`
# which will schedule a sequence function on the next frame, when the sequence fires, it's free to do 
# it's own thing and either return with or without calling `seq.next` again.
# If `seq.next` won't be called, the sequence stops, else if it does, it keeps running on the next frame.
#
# Cue also support minimal sequence events which are just batches of sequences that can be fired by other scripts.
# first `seq.create_event("my_event")` to get an event_id, then `seq.on_event(id, my_func)` to attach a seq. to it.
# Finally fire the event with `seq.fire_event(id)` to fire the seq. (note: you still must re-attach the seq. if you
# want to listen on follow-up event fires, but the event_id is persistent)

class CueSequencer:
    def __init__(self, t: float) -> None:
        self.reset(t)

    def reset(self, t: float) -> None:
        self.next_seqs = []
        self.timed_ts = []
        self.timed_seqs = []
        self.active_events = {}

        self.last_timestamp = t
        self.next_event_id = 65535 # start at the pygame event id limit (to prevent overlap)

    # == sequence api ==

    # schedule a sequence function on the next frame
    def next(self, seq_func: Callable, *args) -> None:
        self.next_seqs.append((seq_func, args))

    # schedule a sequence function after [t] seconds passes (from time of call)
    def after(self, t: float, seq_func: Callable, *args) -> None:
        t += self.last_timestamp
        
        i = bisect_left(self.timed_ts, t)
        self.timed_ts.insert(i, t)
        self.timed_seqs.insert(i, (seq_func, args))

    # request an unused event id, [debug_name] doesn't have to be unique
    def create_event(self, debug_name: str) -> int:
        id = self.next_event_id
        self.next_event_id += 1

        self.active_events[id] = ([], debug_name)

        return id

    # schedule a sequence function to fire with the supplied [event_id]
    def on_event(self, event_id: int, seq_func: Callable, *args) -> None:
        if event_id < 65535 and not event_id in self.active_events:
            # pygame event id, create event seq stack if doesn't exist
            self.active_events[event_id] = ([], f"pygame_{pg.event.event_name(event_id)}")

        try: self.active_events[event_id][0].append((seq_func, args))
        except KeyError: raise KeyError(f"invalid event_id {event_id}!")

    # immidiatelly fire an event and all it's scheduled sequences (aka only returns after all sequences are done)
    def fire_event(self, event_id: int, event_data: Any = None) -> None:
        # freeze the event seq list

        try: ev = self.active_events[event_id]
        except KeyError: raise KeyError(f"invalid event_id {event_id}!")

        seq_list = list(ev[0])
        ev[0].clear()

        # fire sequences (inline)

        if event_data is None:
            for s, a in seq_list:
                s(*a)
        else:
            for s, a in seq_list:
                s(*a, event_data)

    # == game loop api ==

    def tick(self, ct: float) -> None:
        # freeze current seq lists

        next_seqs = list(self.next_seqs)
        self.next_seqs.clear()
        
        i = bisect_right(self.timed_ts, ct)
        timed_seqs = self.timed_seqs[:i]

        self.timed_ts = self.timed_ts[i:]
        self.timed_seqs = self.timed_seqs[i:]

        self.last_timestamp = ct

        # fire sequences

        for s, a in next_seqs:
            s(*a)

        for s, a in timed_seqs:
            s(*a)
    
    def send_event_id(self, event_id: int, event_data: Any = None) -> None:
        # freeze the event seq list

        ev = self.active_events.get(event_id, None)
        if ev is None:
            return

        seq_list = list(ev[0])
        ev[0].clear()

        # fire sequences (inline)

        if event_data is None:
            for s, a in seq_list:
                s(*a)
        else:
            for s, a in seq_list:
                s(*a, event_data)

    # sequences scheduled on the next frame; list[seq_func, seq_args]
    next_seqs: list[tuple[Callable, tuple]]

    # sequences scheduled on a timestamp in the future (waits); keys: list[fire_time] values: list[seq_func, seq_args]
    timed_ts: list[float]
    timed_seqs: list[tuple[Callable, tuple]]

    active_events: dict[int, tuple[list[tuple[Callable, tuple]], str]]

    last_timestamp: float
    next_event_id: int

# == global api ==

from . import cue_state as gs

def next(seq_func: Callable, *args) -> None:
    gs.GameState.sequencer.next(seq_func, *args)

def after(t: float, seq_func: Callable, *args) -> None:
    gs.GameState.sequencer.after(t, seq_func, *args)

def create_event(debug_name: str) -> int:
    return gs.GameState.sequencer.create_event(debug_name)

def on_event(event_id: int, seq_func: Callable, *args) -> None:
    gs.GameState.sequencer.on_event(event_id, seq_func, *args)

def fire_event(event_id: int, event_data: Any = None) -> None:
    gs.GameState.sequencer.fire_event(event_id, event_data)

# static_sequencer is initialized early by the engine itself as many parts of the engine create events with it at init time
gs.GameState.static_sequencer = CueSequencer(time.perf_counter())