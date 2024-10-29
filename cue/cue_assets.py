import os
import pygame as pg
import numpy as np
from typing import Any

from .rendering.cue_resources import GPUMesh, GPUTexture, ShaderPipeline
from . import cue_utils as utils

# == Cue Asset Manager ==

class AssetTypes:
    AUDIO_ASSET = 0
    SURFACE_ASSET = 1
    TEXTURE_ASSET = 2
    MESH_ASSET = 3
    SHADER_ASSET = 4

class AssetManager:
    def __init__(self, asset_dir: str) -> None:
        self.asset_dir = asset_dir
        self.asset_cache = {}

    def reset(self) -> None:
        utils.info(f"[asset_mgr] flushed {len(self.asset_cache)} loaded assets from cache")
        self.asset_cache = {}

    def preload(self, path: str, type_hint: str | None = None) -> None:
        pass

    # == asset access ==

    def check_cache(self, path: str, ex_type: int) -> Any:
        cache = self.asset_cache.get(path, None)
        if cache is not None: # and cache[1] != None:
            if cache[0] != ex_type:
                raise ValueError(f"The assets has been loaded before as a different type! (expected: {ex_type} got: {cache[0]})")

            return cache[1]

    def load_audio(self, path: str) -> pg.mixer.Sound:
        c = self.check_cache(path, AssetTypes.AUDIO_ASSET)
        if c is not None:
            return c

        snd = pg.mixer.Sound(file=os.path.join(self.asset_dir, path))
        self.asset_cache[path] = (AssetTypes.AUDIO_ASSET, snd)

        return snd

    # loads a image file to cpu ram
    def load_surface(self, path: str, cache_surf: bool = True) -> pg.Surface:
        c = self.check_cache(path, AssetTypes.SURFACE_ASSET)
        if c is not None:
            return c

        surf = pg.image.load(os.path.join(self.asset_dir, path), path)

        if cache_surf:
            self.asset_cache[path] = (AssetTypes.SURFACE_ASSET, surf)

        return surf

    # loads a image file to gpu vram; short-hand for load_surface with a texture.write_to()
    def load_texture(self, path: str) -> GPUTexture:
        c = self.check_cache(path, AssetTypes.TEXTURE_ASSET)
        if c is not None:
            return c

        surf = self.load_surface(path, False)

        tex = GPUTexture()
        tex.write_to(surf)
        self.asset_cache[path] = (AssetTypes.TEXTURE_ASSET, tex)

        return tex

    def load_mesh(self, path: str) -> GPUMesh:
        c = self.check_cache(path, AssetTypes.MESH_ASSET)
        if c is not None:
            return c

        with np.load(os.path.join(self.asset_dir, path)) as mesh_data:
            vertex_buf = mesh_data["vert_data"]
            norm_buf = mesh_data["norm_data"]
            uv_buf = mesh_data["uv_data"]

            if "elem_data" in mesh_data:
                elem_buf = mesh_data["elem_data"]
            else:
                elem_buf = None

        mesh = GPUMesh()
        mesh.write_to(vertex_buf, norm_buf, uv_buf, len(vertex_buf), elem_buf, len(elem_buf) if elem_buf is not None else 0)
        self.asset_cache[path] = (AssetTypes.MESH_ASSET, mesh)

        return mesh
    
    def load_shader(self, vs_path: str, fs_path: str) -> ShaderPipeline:
        unique_name = f"(vert: {vs_path}, frag: {fs_path})"

        c = self.check_cache(unique_name, AssetTypes.SHADER_ASSET)
        if c is not None:
            return c

        with open(os.path.join(self.asset_dir, vs_path), 'r') as f:
            vs_src = f.read()

        with open(os.path.join(self.asset_dir, fs_path), 'r') as f:
            fs_src = f.read()
        
        pipe = ShaderPipeline(vs_src, fs_src, unique_name)
        self.asset_cache[unique_name] = (AssetTypes.SHADER_ASSET, pipe)

        return pipe

    # contains already loaded assets, clear with reset()
    asset_cache: dict[str, tuple[int, Any]]

    asset_dir: str