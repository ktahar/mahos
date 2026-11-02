#!/usr/bin/env python3

"""
Tests for mahos.util.math_phys.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.util import math_phys


def test_round_halfint_positive():
    assert math_phys.round_halfint(1.1) == 1.0
    assert math_phys.round_halfint(1.2) == 1.0
    assert math_phys.round_halfint(1.6) == 1.5
    assert math_phys.round_halfint(1.8) == 2.0


def test_round_halfint_negative():
    assert math_phys.round_halfint(-1.1) == -1.0
    assert math_phys.round_halfint(-1.6) == -1.5
    assert math_phys.round_halfint(-1.8) == -2.0


def test_round_evenint():
    assert math_phys.round_evenint(1.0) == 0.0
    assert math_phys.round_evenint(2.0) == 2.0
    assert math_phys.round_evenint(3.0) == 4.0
    assert math_phys.round_evenint(2.2) == 2.0
