#!/usr/bin/env python3

"""
Tests for mahos.gui.param utilities.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.gui.param import _infer_adaptive_min_step
from mahos.msgs.param_msgs import FloatParam, IntParam


def test_infer_adaptive_min_step():
    p = FloatParam(
        0.01,
        0.0,
        100.0,
        digit=6,
        step=0.1,
        adaptive_step=True,
    )
    assert _infer_adaptive_min_step(p) == 1e-7


def test_infer_adaptive_min_step_uses_explicit_value():
    p = FloatParam(
        0.01,
        0.0,
        100.0,
        digit=6,
        step=0.1,
        adaptive_step=True,
        adaptive_min_step=1e-6,
    )
    assert _infer_adaptive_min_step(p) == 1e-6


def test_infer_adaptive_min_step_falls_back_to_bounds():
    p = FloatParam(
        0.0,
        0.0,
        100.0,
        digit=6,
        step=0.1,
        adaptive_step=True,
    )
    assert _infer_adaptive_min_step(p) == 1e-3


def test_infer_adaptive_min_step_none_when_disabled():
    p = FloatParam(0.01, 0.0, 100.0, digit=6, step=0.1, adaptive_step=False)
    assert _infer_adaptive_min_step(p) is None


def test_infer_adaptive_min_step_int_clamped():
    p = IntParam(1000, 0, 100000, digit=6, step=1, adaptive_step=True)
    assert _infer_adaptive_min_step(p) == 1
