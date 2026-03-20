#!/usr/bin/env python3

"""
Type hints and type check helpers for MAHOS.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.msgs.common_msgs import Message, Request, Reply

from typing import NewType, Callable, Union, Tuple

#: NodeName is str hostname::nodename or 2-tuple of str (hostname, nodename)
NodeName = NewType("NodeName", Union[Tuple[str, str], str])

#: SubHandler receives a Message and handle it
SubHandler = NewType("SubHandler", Callable[[Message], None])

#: RepHandler receives a Request and return Reply
RepHandler = NewType("RepHandler", Callable[[Request], Reply])

#: MessageGetter: getter function for Message
MessageGetter = NewType("MessageGetter", Callable[[], Message])


class ConfTypeCheckMixin(object):
    """Mixin to provide type check helper methods for ``self.conf`` entries."""

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
        return v

    def _conf_pos_float(self, key: str, default: float) -> float:
        v = self.conf.get(key, default)
        if not isinstance(v, float):
            raise TypeError(f"{key} must be float. Got {type(v).__name__}: {v!r}")
        if v <= 0.0:
            raise ValueError(f"{key} must be positive float. Got {v}")
        return v

    def _conf_nonneg_float(self, key: str, default: float) -> float:
        v = self.conf.get(key, default)
        if not isinstance(v, float):
            raise TypeError(f"{key} must be float. Got {type(v).__name__}: {v!r}")
        if v < 0.0:
            raise ValueError(f"{key} must be non-negative float. Got {v}")
        return v

    def _conf_num(self, key: str, default: float | int) -> float | int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (float, int)):
            raise TypeError(f"{key} must be float or int. Got {type(v).__name__}: {v!r}")
        return v

    def _conf_pos_num(self, key: str, default: float | int) -> float | int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (float, int)):
            raise TypeError(f"{key} must be float or int. Got {type(v).__name__}: {v!r}")
        if v <= 0.0:
            raise ValueError(f"{key} must be positive number. Got {v}")
        return v

    def _conf_nonneg_num(self, key: str, default: float | int) -> float | int:
        v = self.conf.get(key, default)
        if isinstance(v, bool) or not isinstance(v, (float, int)):
            raise TypeError(f"{key} must be float or int. Got {type(v).__name__}: {v!r}")
        if v < 0.0:
            raise ValueError(f"{key} must be non-negative number. Got {v}")
        return v

    def _conf_bool(self, key: str, default: bool) -> bool:
        v = self.conf.get(key, default)
        if not isinstance(v, bool):
            raise TypeError(f"{key} must be bool. Got {type(v).__name__}: {v!r}")
        return v
