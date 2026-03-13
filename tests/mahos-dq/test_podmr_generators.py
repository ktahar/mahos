#!/usr/bin/env python3

"""
Tests for mahos_dq.meas.podmr_generator.generator.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import pytest

from mahos_dq.meas.podmr_generator.generator import make_generators
from user_generators import AddedGenerator, OverrideRabiGenerator


def test_make_generators_registers_and_overrides_user_generators():
    generators = make_generators(
        generators={
            "my_custom": ["user_generators", "AddedGenerator"],
            "rabi": ["user_generators", "OverrideRabiGenerator"],
        }
    )
    assert isinstance(generators["my_custom"], AddedGenerator)
    assert isinstance(generators["rabi"], OverrideRabiGenerator)


def test_make_generators_rejects_invalid_generator_spec():
    with pytest.raises(TypeError):
        make_generators(generators={"bad": ["only_module_name"]})


def test_make_generators_rejects_non_generator_class():
    with pytest.raises(TypeError):
        make_generators(generators={"bad": ["user_generators", "NotAGenerator"]})


def test_make_generators_rejects_generator_exceeding_max_num_pattern():
    with pytest.raises(ValueError):
        make_generators(
            generators={"bad": ["user_generators", "ThreePatternGenerator"]},
            max_num_pattern=2,
        )
