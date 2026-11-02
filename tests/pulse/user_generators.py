#!/usr/bin/env python3

"""
Test helper generators for make_generators() tests.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos_dq.meas.podmr_generator.generator import PatternGenerator, RabiGenerator


class AddedGenerator(PatternGenerator):
    """Minimal custom generator for registry tests."""

    def _generate(
        self,
        xdata,
        common_pulses: list[float],
        pulse_params: dict,
        partial: int,
        reduce_start_divisor: int,
        fix_base_width: int | None,
    ):
        return [], self.freq, common_pulses


class OverrideRabiGenerator(RabiGenerator):
    """Custom class used to override built-in rabi."""

    pass


class ThreePatternGenerator(AddedGenerator):
    """Generator with unsupported pattern count for allowed_num_pattern tests."""

    def num_pattern(self) -> int:
        return 3


class NotAGenerator(object):
    """Invalid class for type-check tests."""

    pass
