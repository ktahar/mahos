#!/usr/bin/env python3

"""
Config utility module.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

Defines utilities for configs.

"""

from __future__ import annotations
import typing as T
import enum
import math


class ConfAccessorMixin(object):
    """Mixin providing validated access to ``self.conf`` entries."""

    def _conf_str(self, key: str, default: str) -> str:
        v = self.conf.get(key, default)
        if not isinstance(v, str):
            raise TypeError(f"{key} must be str. Got {type(v).__name__}: {v!r}")
        return v

    def _conf_int(self, key: str, default: int) -> int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"{key} must be int. Got {type(v).__name__}: {v!r}")
        return v

    def _conf_pos_int(self, key: str, default: int) -> int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"{key} must be int. Got {type(v).__name__}: {v!r}")
        if v <= 0:
            raise ValueError(f"{key} must be positive int. Got {v}")
        return v

    def _conf_nonneg_int(self, key: str, default: int) -> int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"{key} must be int. Got {type(v).__name__}: {v!r}")
        if v < 0:
            raise ValueError(f"{key} must be non-negative int. Got {v}")
        return v

    def _conf_float(self, key: str, default: float) -> float:
        v = self.conf.get(key, default)
        if not isinstance(v, float):
            raise TypeError(f"{key} must be float. Got {type(v).__name__}: {v!r}")
        if not math.isfinite(v):
            raise ValueError(f"{key} must be finite float. Got {v}")
        return v

    def _conf_pos_float(self, key: str, default: float) -> float:
        v = self.conf.get(key, default)
        if not isinstance(v, float):
            raise TypeError(f"{key} must be float. Got {type(v).__name__}: {v!r}")
        if not math.isfinite(v) or v <= 0.0:
            raise ValueError(f"{key} must be positive finite float. Got {v}")
        return v

    def _conf_nonneg_float(self, key: str, default: float) -> float:
        v = self.conf.get(key, default)
        if not isinstance(v, float):
            raise TypeError(f"{key} must be float. Got {type(v).__name__}: {v!r}")
        if not math.isfinite(v) or v < 0.0:
            raise ValueError(f"{key} must be non-negative finite float. Got {v}")
        return v

    def _conf_num(self, key: str, default: float | int) -> float | int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (float, int)):
            raise TypeError(f"{key} must be float or int. Got {type(v).__name__}: {v!r}")
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError(f"{key} must be finite number. Got {v}")
        return v

    def _conf_pos_num(self, key: str, default: float | int) -> float | int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (float, int)):
            raise TypeError(f"{key} must be float or int. Got {type(v).__name__}: {v!r}")
        if isinstance(v, float) and not math.isfinite(v) or v <= 0.0:
            raise ValueError(f"{key} must be positive finite number. Got {v}")
        return v

    def _conf_nonneg_num(self, key: str, default: float | int) -> float | int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (float, int)):
            raise TypeError(f"{key} must be float or int. Got {type(v).__name__}: {v!r}")
        if isinstance(v, float) and not math.isfinite(v) or v < 0.0:
            raise ValueError(f"{key} must be non-negative finite number. Got {v}")
        return v

    def _conf_bool(self, key: str, default: bool) -> bool:
        v = self.conf.get(key, default)
        if not isinstance(v, bool):
            raise TypeError(f"{key} must be bool. Got {type(v).__name__}: {v!r}")
        return v


class PresetLoader(object):
    class Mode(enum.Enum):
        EXACT = 0
        PARTIAL = 1
        FORWARD = 2
        BACKWARD = 3

    def __init__(self, logger, mode: Mode = Mode.EXACT):
        self.logger = logger
        self.mode = mode
        self.presets = {}

    def add_preset(self, name: str, preset: list[tuple[str, T.Any]]):
        self.presets[name] = preset

    def load_or_warn(self, conf, key, value):
        if key in conf:
            msg = f"conf[{key}] = {conf[key]} exists. Not loading preset value {value}."
            self.logger.warn(msg)
        else:
            conf[key] = value
            self.logger.debug(f"Load conf[{key}] = {conf[key]}")

    def search_preset(self, name: str):
        for key in self.presets:
            if (
                (self.mode == self.Mode.EXACT and name == key)
                or (self.mode == self.Mode.PARTIAL and key in name)
                or (self.mode == self.Mode.FORWARD and name.startswith(key))
                or (self.mode == self.Mode.BACKWARD and name.endswith(key))
            ):
                return key
        return None

    def load_preset(self, conf: dict, name: str):
        n = self.search_preset(name)
        if n is None:
            self.logger.warn(f"Cannot load preset due to unknown name {name}.")
            return
        self.logger.info(f"Loading preset {n}.")
        for key, value in self.presets[n]:
            self.load_or_warn(conf, key, value)
