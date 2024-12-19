# Cue Entities

Entities in Cue refer to any object present in a map, like models, triggers, enemies or the player itself. Each entity has assigned its *entity type* and initial *entity data*. 

## Overview of Entities

An *Entity* in Cue is what maps are made from, they can represent models, colliders, more complex object like enemies and the player or tag entities like nav nodes for other AI entities. An instance of an *Entity* has two main parts:
- *Entity Type* - a python class or collection of functions that define the behavior of the entity, it provides the functions to the Cue engine which will be called when entity is spawned, despawned, etc. (see *Basic Entity Type* bellow)
- *Entity Data* - a `dict` which contains "json-fiable" fields, it's passed to the *Entity Type* implementation on entity creation and contains initial state of the entity. Things like position, rotation, mesh and textures to use and other entity type specific fields.

*Entities* can be then spawned by the engine (either directly from game code over `GameState.entity_storage`) or when loading from maps. When an entity is spawned, its entity types `spawn()` function is called to initialize it's state and Cue sequences. (see `seq_guide.md` for how to use sequences) The *Entity* instance then continues to exists in the background. (updated externaly or by its sequences set up in `spawn()`)

Later the *Entity* will be despawned and `despawn()` from its entity type will be called, this is when the entity type should "clean up" itself from the engine (like despawning models and hitboxes from engine)

## Basic Entity Type

An *Entity Type* is a collection of python functions or classes which are called by the engine when processing an entity of that type. An example of an *Entity Type* might be the built-in type `bt_static_mesh`, lets look how it's written under the hood (full source code in `cue/entities/bt_static_mesh.py`)

```python
from dataclasses import dataclass
from . import cue_entity_types as en

from ..components.cue_transform import Transform
from ..components.cue_model import ModelRenderer

# a simple built-in static mesh for map building

@dataclass(init=False, slots=True)
class BtStaticMesh:
    def __init__(self, en_data: dict) -> None:
        self.mesh_trans = Transform(Vec3(en_data["t_pos"]), Vec3(en_data["t_rot"]), Vec3(en_data["t_scale"]))
        self.mesh_renderer = ModelRenderer(en_data, self.mesh_trans)

    # == entity hooks ==

    @staticmethod
    def spawn(en_data: dict) -> 'BtStaticMesh':
        return BtStaticMesh(en_data)

    def despawn(self) -> None:
        self.mesh_renderer.despawn()

    # ... dev tick code ...

    mesh_trans: Transform
    mesh_renderer: ModelRenderer
```

That's a lot but let's break it down. First we define a new class `BtStaticMesh` for our entity, this class will be used for "holding" our entities variables between frames. Then we define a `__init__` function which takes *Entity Data* (which come from the map file or the `entity.spawn()` caller) and sets up the initial variables.

Here is the first use of *Cue Components*, they are usually chunks of code which are reused between a lot of entity types and so were made into their own reusable thing. In this instance we have the `Transform` component and the `ModelRenderer` component, if you ever worked with these they do exactly what their name suggests, `Transform` hold the position, rotation and scale of the entity and `ModelRenderer` does the heavy lifting with calling the low-level Cue rendering backend for putting a 3D model in the map.

Then we define `spawn()` and `despawn(self)` functions, these are described by the comment above as "entity hooks" because these are the functions which are called directly by the engine, We'll see how later. Note that *Components* often also have their own "entity hook" functions exposed which must be called by the *Entity Type*. (eg. in this case `ModelRenderer.despawn()`)

### Dev Ticks

There is one part of the `BtStaticMesh` class i left out before and that's the *dev tick* entity hook. This functions is **never** called when normally playing, it's only used when the map editor is running.

It's used for entity specific editor code. (like edit mode, initial position after spawn and preview model in viewport)

```python
from .cue_entity_utils import handle_transform_edit_mode

# ... BtStaticMesh code ...

	def despawn(self) -> None:
	    self.mesh_renderer.despawn()
    
	@staticmethod
	def dev_tick(s: dict | None, dev_state: en.DevTickState, en_data: dict) -> dict:
		if s is None:
			# init mesh
			
			if en_data["t_pos"] is None:
				en_data["t_pos"] = dev_state.suggested_initial_pos
			
			s = {"mesh": BtStaticMesh(en_data), "en_data": dict(en_data)}
		
		if dev_state.is_entity_selected:
			# handle trasnsform editing
			handle_transform_edit_mode(s, dev_state, en_data)
		
		return s
	
    mesh_trans: Transform
    mesh_renderer: ModelRenderer
```

Since `dev_tick` is one of the less clean entity hooks out there, let's break it down once more. The *dev tick* function takes three parameters `state`, `dev_state` and `en_data`.  

- `s` is a "state" like var that's *dev tick* function specific. The first time a *dev tick* is called for a specific entity in the map it's set to `None`, after the first call, the **return value** from the last *dev tick* is passed back into the `s` parameter, it is usually used to preserve state between *dev tick* calls.
- `dev_state` is a collection of vars supplied by the editor, it contains convenience vars like `suggested_initial_pos`, (a position where a new entity should spawn that tick) `is_entity_selected`, (eg. for highlighting) `view_pos`, etc. 
- `en_data` is the same exact `dict` you get when `spawn()` is called and gives you info on "what entity" is supped to be previewed to the viewport (note: as `en_data` is a reference to the editors internal state it can be safely edited by the *dev tick* function and changes will be visible to the engine after)

> [!note]
> in this example, `BtStaticMesh` is directly used in it's *dev tick*, this is usually not how *dev ticks* are implemented as it's purpose is to avoid running run-time code in the editor. Here `BtStaticMesh` is used directly because to preview a static model in the scene is the same as showing it in-game, other *Entity Types* also either use `BtStaticMesh` in their own *dev ticks*, make use of the `rendering.cue_gizmos` module or both to draw their previews.

### Finalizing Types

Now that we have our *Entity Type*, we'll register it with the engine.

```python
def gen_def_data():
    return {
        "t_pos": None, # will be filled by "suggested_initial_pos"
        "t_rot": Vec3([0.0, 0.0, 0.0]),
        "t_scale": Vec3([1.0, 1.0, 1.0]),
        "a_model_mesh": "models/icosph.npz",
        "a_model_vshader": "shaders/base_cam.vert",
        "a_model_fshader": "shaders/unlit.frag",
        "a_model_albedo": "textures/def_white.png",
        "a_model_transparent": False,
        "a_model_uniforms": {},
    }

en.create_entity_type("bt_static_mesh", BtStaticMesh.spawn, BtStaticMesh.despawn, BtStaticMesh.dev_tick, gen_def_data)
```

First as a QoL feature for the editor, we define a function for generating the "default" *Entity Data* to be used as the initial data for a newly created entity *in the editor*.

Then we make a last call to `create_entity_type()` which will insert your *Entity Type* into the engines *Entity Type Registry* and make it available to be used in the editor and by maps. The `create_entity_type()` call takes `type_name` (engine-wide unique name, ideally prefixed with the project shorthand, built-in types are prefixed with `bt_`) and the individual "entity hook" functions.

> [!note]
> When implementing *Entity Types* in multiple python files, it's possible that your types won't show up in the engine. That's because the file with your implementation (`bt_static_mesh.py` in this case) must be **imported** in your codebase at least once so your type has a chance to register with the engine.
> 
> Best practice is usually to have a block of imports in your `main.py` and `editor.py` that'll import all your entity implementations.
> ```python
> # == import entity types ==
> import bt_static_mesh
> import my_entity_type
> ```