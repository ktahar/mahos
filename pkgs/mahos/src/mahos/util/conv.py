#!/usr/bin/env python3

"""
Conversion utility module.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

Defines generic / miscellaneous conversion functions.

"""

from __future__ import annotations
import typing as T
import warnings

import numpy as np


def step_to_num(start, stop, step, decimals=10):
    return int(round(abs((stop - start) / float(step)), decimals)) + 1


def num_to_step(start, stop, num):
    try:
        return abs(stop - start) / float(abs(num) - 1)
    except Exception:
        return 0.0


K = T.TypeVar("K")
V = T.TypeVar("V")


def args_to_list(args: tuple[list[V] | tuple[V, ...]] | list[V] | tuple[V, ...] | V) -> list[V]:
    """Convert possibly nested (dim = 2) / raw (dim = 0) arguments to list of values (dim = 1).

    Useful for functions accepting variable-length args (*args).
    Conversion examples:
    - [[v0, v1, ...]] -> [v0, v1, ...]
    - [v0, v1, ...] -> [v0, v1, ...]
    - v0 -> [v0]

    """

    if len(args) == 1:
        if isinstance(args[0], (list, tuple)):
            return list(args[0])
        else:
            return [args[0]]
    return args


def invert_mapping(d: T.Mapping[K, V]) -> dict[V, list[K]]:
    """Invert given mapping.

    New values (original keys) are stored as lists
    because the keys (original values) can be same for multiple values
    (Mapping is not always injective).

    """

    ret = {}
    for key, value in d.items():
        if value in ret:
            ret[value].append(key)
        else:
            ret[value] = [key]
    return ret


def _clip_angle(theta, min_, max_, step):
    while theta < min_:
        theta += step
    while theta > max_:
        theta -= step
    return theta


def clip_angle_degrees(theta: float | np.ndarray, min_=0.0, max_=360.0) -> float | np.ndarray:
    return _clip_angle(theta, min_, max_, 360.0)


def clip_angle_radians(theta: float | np.ndarray, min_=0.0, max_=2 * np.pi) -> float | np.ndarray:
    return _clip_angle(theta, min_, max_, 2 * np.pi)


def real_fft(xdata, ydata, remove_dc=True):
    """Deprecated alias for :func:`mahos.util.signal.real_fft`."""

    import mahos.util.signal

    warnings.warn(
        "mahos.util.conv.real_fft is deprecated; use mahos.util.signal.real_fft instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mahos.util.signal.real_fft(xdata, ydata, remove_dc=remove_dc)


def real_fftfreq(xdata):
    """Deprecated alias for :func:`mahos.util.signal.real_fftfreq`."""

    import mahos.util.signal

    warnings.warn(
        "mahos.util.conv.real_fftfreq is deprecated; use mahos.util.signal.real_fftfreq instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mahos.util.signal.real_fftfreq(xdata)
