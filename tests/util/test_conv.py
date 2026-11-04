#!/usr/bin/env python3

"""
Tests for mahos.util.conv.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from mahos.util import conv


def test_step_num_roundtrip():
    num = conv.step_to_num(0.0, 10.0, 2.0)
    assert num == 6
    assert conv.num_to_step(0.0, 10.0, num) == 2.0


def test_num_to_step_invalid():
    assert conv.num_to_step(0.0, 10.0, 1) == 0.0


def test_args_to_list_variants():
    assert conv.args_to_list(([1, 2, 3],)) == [1, 2, 3]
    assert conv.args_to_list((5,)) == [5]
    assert conv.args_to_list((1, 2)) == (1, 2)


def test_invert_mapping():
    src = {"a": 1, "b": 1, "c": 2}
    assert conv.invert_mapping(src) == {1: ["a", "b"], 2: ["c"]}


def test_clip_angle_degrees():
    assert conv.clip_angle_degrees(450.0) == 90.0
    assert conv.clip_angle_degrees(-90.0) == 270.0


def test_clip_angle_radians():
    two_pi = 2.0 * np.pi
    assert conv.clip_angle_radians(two_pi + 0.1) == pytest.approx(0.1)
