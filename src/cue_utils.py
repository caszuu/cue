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
    exit(-1)
