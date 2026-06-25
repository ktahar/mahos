#!/usr/bin/env python3

"""
Tests for Spectrum utility functions.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos_dq.util.spectrum import (
    round_duration_for_spectrum_segment,
    round_spectrum_segment_samples,
    valid_spectrum_segment_samples,
)


def test_round_spectrum_segment_samples():
    assert round_spectrum_segment_samples(1) == 32
    assert round_spectrum_segment_samples(32) == 32
    assert round_spectrum_segment_samples(33) == 48


def test_valid_spectrum_segment_samples():
    assert not valid_spectrum_segment_samples(16)
    assert valid_spectrum_segment_samples(32)
    assert not valid_spectrum_segment_samples(40)
    assert valid_spectrum_segment_samples(48)


def test_round_duration_for_spectrum_segment():
    duration, samples = round_duration_for_spectrum_segment(
        duration=10, base=4, sample_factor=3, sample_divisor=2
    )

    assert duration >= 10
    assert duration % 4 == 0
    assert samples == duration * 3 // 2
    assert valid_spectrum_segment_samples(samples)
