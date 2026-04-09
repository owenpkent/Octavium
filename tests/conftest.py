"""Stub out heavy dependencies that aren't needed for pure-logic tests."""

import sys
import types

# modulune/__init__.py imports .engine which imports pygame and PySide6 via
# app.midi_io. Preload modulune as a bare namespace package so that
# `from modulune.harmony import ...` works without triggering __init__.py's
# eager import of engine.py.

_mod = types.ModuleType("modulune")
_mod.__path__ = [__import__("pathlib").Path(__file__).resolve().parent.parent.joinpath("modulune").as_posix()]
_mod.__package__ = "modulune"
sys.modules.setdefault("modulune", _mod)
