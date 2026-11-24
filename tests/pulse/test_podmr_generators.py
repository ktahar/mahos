#!/usr/bin/env python3

"""
Tests for mahos_dq.meas.podmr_generator.generator.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from mahos_dq.meas.podmr_generator import generator_kernel as K
from mahos_dq.meas.podmr_generator.splitter import IntervalSplitter
from mahos_dq.msgs.podmr_msgs import MWMode

from mahos_dq.meas.podmr_generator.generator import PatternGenerator, make_generators
from user_generators import AddedGenerator, OverrideRabiGenerator


def test_make_generators_registers_and_overrides_user_generators():
    splitter = IntervalSplitter({"split_head": 20e-9})
    generators = make_generators(
        generators={
            "my_custom": ["user_generators", "AddedGenerator"],
            "rabi": ["user_generators", "OverrideRabiGenerator"],
        },
        splitter=splitter,
    )
    assert isinstance(generators["my_custom"], AddedGenerator)
    assert isinstance(generators["rabi"], OverrideRabiGenerator)
    assert all(generator.splitter is splitter for generator in generators.values())


def test_make_generators_rejects_legacy_split_fraction_init():
    with pytest.raises(TypeError, match="splitter"):
        make_generators(generators={"legacy": ["user_generators", "LegacyInitGenerator"]})


def test_make_generators_rejects_invalid_generator_spec():
    with pytest.raises(TypeError):
        make_generators(generators={"bad": ["only_module_name"]})


def test_make_generators_rejects_non_generator_class():
    with pytest.raises(TypeError):
        make_generators(generators={"bad": ["user_generators", "NotAGenerator"]})


def test_make_generators_rejects_generator_with_disallowed_num_pattern():
    with pytest.raises(ValueError):
        make_generators(
            generators={"bad": ["user_generators", "ThreePatternGenerator"]},
            allowed_num_pattern=(2,),
        )


def test_interval_splitter_fixed_and_warnings():
    warnings = []
    splitter = IntervalSplitter(
        {"split_head": 2.4e-9, "min_split_tail": 1.1e-9, "split_fraction": 0}, warnings.append
    )
    assert len(warnings) == 1 and "split_fraction is disregarded" in warnings[0]
    assert splitter.ticks_to_preserve(1e9) == (2,)
    assert splitter.split(4, 1e9, 1e9) == (2, 2)
    with pytest.raises(ValueError, match=r"split_head \(2 ticks\) \+ min_split_tail \(2 ticks\)"):
        splitter.split(3, 1e9, 1e9)
    assert splitter.split(2, 1e9, 5e8) == (1, 1)
    with pytest.raises(ValueError):
        splitter.split(0, 1e9, 1e9)
    assert IntervalSplitter({"split_head": 0}).split(0, 1e9, 1e9) == (0, 0)
    assert IntervalSplitter({"split_head": 2e-9}).split(2, 1e9, 1e9) == (2, 0)
    legacy = IntervalSplitter({"min_split_tail": -1}, warnings.append)
    assert "min_split_tail is disregarded" in warnings[-1]
    assert legacy.split(4, 1e9, 1e9) == (1, 3)


@pytest.mark.parametrize(
    "conf", [{"split_fraction": 0}, {"split_head": 20e-9, "min_split_tail": -1}]
)
def test_interval_splitter_rejects_invalid_active_settings(conf):
    with pytest.raises(ValueError):
        IntervalSplitter(conf)


@pytest.mark.parametrize(
    "min_tail, freq, minimum",
    [(61e-9, 1e9, 61), (70e-9, 1e8, 7), (61.000001e-9, 1e9, 62)],
)
def test_interval_splitter_min_tail_tick_boundary(min_tail, freq, minimum):
    splitter = IntervalSplitter({"split_head": 0, "min_split_tail": min_tail})
    assert splitter.split(minimum, 2e9, freq) == (0, minimum)
    with pytest.raises(ValueError, match="Cannot split interval"):
        splitter.split(minimum - 1, 2e9, freq)


def test_interval_splitter_rejects_unpreserved_head():
    splitter = IntervalSplitter({"split_head": 2.5e-9})
    # 5 ticks at 2 GHz cannot be reduced to 1 GHz; this happens when rounding bypasses
    # ticks_to_preserve.
    with pytest.raises(ValueError, match="split_head .* is not representable"):
        splitter.split(100, 2e9, 1e9)
    assert splitter.split(100, 2e9, 2e9) == (5, 95)


@pytest.mark.parametrize(
    "head, expected_freq", [(None, 1e7), (2.5e-9, 2e9), (3e-9, 1e9), (30e-9, 1e8)]
)
def test_fixed_head_limits_reduction(head, expected_freq):
    splitter = IntervalSplitter({} if head is None else {"split_head": head})
    freq, xdata, common, p0, p1 = K.round_pulses(
        2e9,
        [100e-9],
        [200e-9],
        [300e-9],
        [400e-9],
        2,
        lambda _: None,
        ticks_to_preserve=splitter.ticks_to_preserve(2e9),
    )
    assert freq == expected_freq
    assert [xdata[0] / freq, common[0] / freq, p0[0] / freq, p1[0] / freq] == pytest.approx(
        [100e-9, 200e-9, 300e-9, 400e-9]
    )
    if head is not None:
        assert splitter.split(xdata[0], 2e9, freq)[0] / freq == pytest.approx(head)


def _generator_params(generator, pulse_overrides):
    pulse = generator.pulse_params().unwrap()
    pulse.update(pulse_overrides)
    return {
        "base_width": 100e-9,
        "laser_delay": 100e-9,
        "laser_width": 100e-9,
        "mw_delay": 100e-9,
        "trigger_width": 100e-9,
        "init_delay": 100e-9,
        "final_delay": 100e-9,
        "partial": 0,
        "enable_reduce": True,
        "pulse": pulse,
    }


@pytest.mark.parametrize(
    "label, mode, expected_freq",
    [
        ("rabi", MWMode.QPSK, 10e6),
        ("custom_rabi", MWMode.QPSK, 10e6),
        ("fid", MWMode.Ext2Phase, 10e6),
        ("fid", MWMode.QPSK, 2e9),
        ("trse", MWMode.Ext2Phase, 10e6),
        ("trse", MWMode.QPSK, 2e9),
    ],
)
def test_fixed_head_constrains_only_split_paths(label, mode, expected_freq):
    generator = make_generators(
        splitter=IntervalSplitter({"split_head": 2.5e-9}),
        mw_modes=(mode,),
        generators={"custom_rabi": ["user_generators", "OverrideRabiGenerator"]},
        print_fn=lambda _: None,
    )[label]
    params = _generator_params(
        generator,
        {"90pulse": 100e-9, "180pulse": 200e-9, "270pulse": 300e-9, "tauconst": 100e-9},
    )
    _, freq, _ = generator.generate_raw_blocks([100e-9], params)
    assert freq == expected_freq


@pytest.mark.parametrize("enable_reduce", [False, True])
def test_xy4_fixed_head(enable_reduce):
    params = {
        "base_width": 320e-9,
        "laser_delay": 40e-9,
        "laser_width": 5e-6,
        "mw_delay": 1e-6,
        "trigger_width": 20e-9,
        "init_delay": 0.0,
        "final_delay": 5e-6,
        "partial": 0,
        "enable_reduce": enable_reduce,
        "pulse": {
            "90pulse": 10e-9,
            "180pulse": 20e-9,
            "Nconst": 1,
            "readY": False,
            "invertY": False,
            "supersample": 1,
        },
    }
    generator = make_generators(
        splitter=IntervalSplitter({"split_head": 30e-9, "min_split_tail": 10e-9}),
        print_fn=lambda _: None,
    )["xy4"]
    blocks, freq, _ = generator.generate_raw_blocks([100e-9, 200e-9], params)
    legacy, legacy_freq, _ = make_generators(print_fn=lambda _: None)["xy4"].generate_raw_blocks(
        [100e-9, 200e-9], params
    )
    for group, old_group in zip(blocks, legacy):
        assert group.total_length() / freq == pytest.approx(old_group.total_length() / legacy_freq)
        pattern = group[0].pattern
        # Inspect actual phase changes between MW pulses (XY4 also has equal-phase neighbors).
        elapsed = 0
        mw_end = None
        mw_intervals = []
        changes = []
        previous = None
        for channels, duration in pattern:
            if "mw" in channels:
                mw_intervals.append((elapsed / freq, (elapsed + duration) / freq))
                mw_end = elapsed + duration
            elif previous is not None and "mw" not in previous and channels != previous:
                if mw_end is not None:
                    changes.append((elapsed - mw_end) / freq)
            elapsed += duration
            previous = channels
        assert len(changes) >= 3
        assert changes == pytest.approx([30e-9] * len(changes))
        old_elapsed = 0
        old_intervals = []
        for channels, duration in old_group[0].pattern:
            if "mw" in channels:
                old_intervals.append(
                    (old_elapsed / legacy_freq, (old_elapsed + duration) / legacy_freq)
                )
            old_elapsed += duration
        assert np.array(mw_intervals) == pytest.approx(np.array(old_intervals))
    with pytest.raises(ValueError, match="Cannot split interval"):
        generator.generate_raw_blocks([30e-9], params)
