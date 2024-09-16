import sys
from typing import TypeVar, Generic

# == Cue Utilities ==

bold_escape = "\x1b[1m"
error_escape = f"{bold_escape}\x1b[31m"
warning_escape = f"{bold_escape}\x1b[33m"
debug_escape = f"{bold_escape}\x1b[94m"
reset_escape = "\x1b[0m"

def debug(message: str) -> None:
    print(f"[{debug_escape}debug{reset_escape}] {message}")

def info(message: str) -> None:
    print(f"[{bold_escape}info{reset_escape}] {message}")

def warn(message: str) -> None:
    print(f"[{warning_escape}warn{reset_escape}] {message}")

def error(message: str) -> None:
    print(f"[{error_escape}error{reset_escape}] {message}")

def abort(message: str) -> None:
    print(f"[{error_escape}critical{reset_escape}] {message}")
    sys.exit(-1)

# matrix transform utils
# again everything is sourced from https://songho.ca/index.html

import numpy as np
import math

def mat4_translate(offset: tuple[float, float, float]) -> np.ndarray:
    x, y, z = offset
    
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1],
    ], dtype=np.float32)

def mat4_scale(scale: tuple[float, float, float]) -> np.ndarray:
    x, y, z = scale
    
    return np.array([
        [x, 0, 0, 0],
        [0, y, 0, 0],
        [0, 0, z, 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)

def mat4_rotate(angle: float, axis: tuple[float, float, float]) -> np.ndarray:
    x = axis[0]
    y = axis[1]
    z = axis[2]

    s = math.sin(angle)
    c = math.cos(angle)
    nc = 1 - c

    return np.array([
        [nc * (x ** 2) + c, nc * x * y - s * z, nc * x * z + s * y, 0],
        [nc * x * y + s * z, nc * (y ** 2) + c, nc * y * z - s * x, 0],
        [nc * x * z - s * y, nc * y * z + s * x, nc * (z ** 2) + c, 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)
