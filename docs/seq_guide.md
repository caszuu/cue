# Cue Sequences

This is an introduction to Cue Sequences which are the basic building block for scripting in Cue.

### Pygame game loop

When you're making a simple game in pygame, you're app structure probably looks similar to this
```py
import pygame

# ... do setup stuff ...

while True:
    # ... do per-frame stuff ...
```

Here you put *all* the code that needs to run every frame into a single while loop, while this is fine for small projects, it quickly becomes hard to manage.

### Cue game loop

In Cue, outside your app's `main.py`, the while loop doesn't exist. Instead you use the `cue_sequence` module to loop your code when needed.
Sequences are a fancy name for functions that are scheduled to be run in the future, simple as that. This can then be used to create more complex patterns like ticks (while loops) and timers.

```py
import cue.cue_sequence as seq

def my_tick_func():
    print(f"new frame, yippe!")
    seq.next(my_tick_func)

seq.next(my_tick_func)
```

### `seq.next` - call *next* frame

This is the simplest and most common use, simply schedule a function to be called next frame.
```py
import cue.cue_sequence as seq

def do_stuff():
    # ... important stuff ...

seq.next(do_stuff) # call do_stuff() on the next frame from now
```

This way, `do_stuff()` will be called *one* frame after the `seq.next` call, but only **once**. This is because sequences are not persistent and delete themself when being fired. (aka every individual sequence will fire only once)

To contruct a loop, we need to call `seq.next` *again* in the function itself
```py
import cue.cue_sequence as seq

def do_stuff():
    # ... important stuff ...
    seq.next(do_stuff) # call itself *again* a frame later

seq.next(do_stuff)
```

And that's all, we just constructed a tick function! If we want to stop the function at some point, simply don't call `seq.next` that time.

#### Sequences with State

Pro Tip: You've probbaly noticed that in this model there's no place to store variables between sequence calls. While you can't directly share data between sequences, you can pass multiple variables to `seq` calls which will forward the data to the next iteration.

```py
import cue.cue_sequence as seq

def do_stuff(state, counter):
    # ... important stuff ...
    seq.next(do_stuff, state, counter + 1) # forward wanted data to the next iteration

seq.next(do_stuff, {"pos": 0, "vel": 1}, 0) # pass initial values to the loop
```

### `seq.after` - call *after* some time

This function is nearly identical to `seq.next` except in one thing, it fires the sequence after a specified number of seconds instead of immediately next frame. A simple example of a timer:
```py
import cue.cue_sequence as seq

def start_action(data):
    # ... do action ...

seq.after(4.5, start_action, [1, 2, 3]) # call start_action() after 4.5s from now
```

### `seq.on_event` - call *on* an event

Cue events are a part of the sequence system, they cover both pygame events (`pygame.KEYDOWN`, `pygame.QUIT`, etc.) and custom events which are created by the Cue game code.

`seq.on_event` is similar to the previous functions in that it schedules a sequence, but this it schedules it to fire when a specific event happens
```py
import pygame as pg
import cue.cue_sequence as seq

def on_key_down(e):
    if e.key == pg.K_e:
        # ... do stuff ...

    seq.on_event(pg.KEYDOWN, on_key_down) # re-schedule for that event type

seq.on_event(pg.KEYDOWN, on_key_down) # schedule on_key_down() to be fired when a "pg.KEYDOWN" event happens
```
Notice two things. First, like with the other `seq` functions, we have to re-schedule in order to not stop receiving events for the same reason as last time. Second, the `on_key_down()` function has a parameter which is not filled by the `seq.on_event` calls, this is because the *last* parameter to an event sequence will be filled by the event data (it's still possible to pass in data using `seq.on_event` like before, they will be put before the event data parameter)

### `seq.create_event`, `cue.fire_event` and Custom Events

Using `seq.create_event` you can use the sequence event system for non-pygame events, they work exactly like pygame events except they are created and fired by the game code.

A simple full custom event example
```py
import cue.cue_sequence as seq

my_event_id = seq.create_event("my_event") # create a new event type with a debug name "my_event"

# ... some code ...

def on_my_event(e):
    if e == 0:
        # ... do stuff ...
    elif e == 1:
        # ... do other stuff ...

    seq.on_event(my_event_id, on_my_event)

seq.on_event(my_event_id, on_my_event) # schedule on_my_event() to be fired when a "my_event" event is fired

# ... some more code ...

seq.fire_event(my_event_id, 0) # fire the "my_event" event with event data being `0`
```

Here we first create a new event and give it a *debug* name "my_event" (this name is mostly irrelevant and only used to display a name for the event in the editor), then we schedule a sequence to fire with our custom event, and lastly we fire the event with event data being `0`, the `seq.fire_event` will cause `on_my_event()` and any other scheduled sequences to fire *immediatelly*.