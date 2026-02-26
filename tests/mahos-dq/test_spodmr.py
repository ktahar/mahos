#!/usr/bin/env python3

"""
Tests for mahos_dq.meas.spodmr.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import copy

import numpy as np

from mahos_dq.meas.spodmr import SPODMRClient, SPODMRIO
from mahos_dq.meas.spodmr_worker import BlockSeqBuilder
from mahos_dq.msgs.spodmr_msgs import SPODMRData
from mahos_dq.meas.podmr_generator.generator import make_generators
from mahos.msgs.common_msgs import BinaryState
from util import get_some, expect_value, save_load_test
from fixtures import ctx, gconf, server, spodmr, server_conf, spodmr_conf


def expect_spodmr(cli: SPODMRClient, num: int, poll_timeout_ms):
    def get():
        data: SPODMRData = cli.get_data()
        if data is not None and data.data0 is not None:
            return data.data0.shape[0]
        else:
            return None

    return expect_value(get, num, poll_timeout_ms, trials=500)


def _spodmr_params() -> dict:
    return {
        "base_width": 0.0,
        "trigger_width": 0.0,
        "init_delay": 0.0,
        "final_delay": 0.0,
        "fix_base_width": 1,
        "laser_delay": 45e-9,
        "laser_width": 3e-6,
        "mw_delay": 1e-6,
        "enable_reduce": False,
        "partial": -1,
        "accum_window": 100e-6,
        "accum_rep": 2,
        "drop_rep": 1,
        "lockin_rep": 1,
        "pd_rate": 500e3,
        "pulse": {},
    }


def _build_spodmr_blockseq(xdata: np.ndarray, params: dict):
    generators = make_generators()
    blocks, freq, common_pulses = generators["rabi"].generate_raw_blocks(xdata, params)
    builder = BlockSeqBuilder(
        trigger_width=1e-6,
        nest=False,
        block_base=4,
        eos_margin=0,
        mw_modes=(0,),
        iq_amplitude=0.0,
        channel_remap=None,
    )
    blockseq, _, _, _ = builder.build_blocks(
        blocks, freq, common_pulses, params, sync_mode="lockin", num_mw=1
    )
    return blockseq, freq, blocks, builder


def _pattern_map(blockseq):
    channels, patterns = blockseq.decode_all()
    return {ch: p for ch, p in zip(channels, patterns)}


def test_spodmr_mw_offset_per_unit():
    xdata = np.array([120e-9])
    params = _spodmr_params()
    blockseq_ref, freq, raw_blocks, builder = _build_spodmr_blockseq(xdata, params)
    ref_patterns = _pattern_map(blockseq_ref)

    offset_ticks = 37
    params_offset = copy.deepcopy(params)
    params_offset["mw_offset"] = offset_ticks / freq
    blockseq_ofs, _, _, _ = _build_spodmr_blockseq(xdata, params_offset)
    ofs_patterns = _pattern_map(blockseq_ofs)

    assert blockseq_ref.total_length() == blockseq_ofs.total_length()
    mw_changed = False
    for ch, p_ref in ref_patterns.items():
        p_ofs = ofs_patterns[ch]
        if isinstance(ch, str) and ch.startswith("mw"):
            mw_changed |= not np.array_equal(p_ref, p_ofs)
        else:
            assert np.array_equal(p_ref, p_ofs)
    assert mw_changed

    blks = raw_blocks[0].remove("trigger").remove("sync")
    unit_ticks = builder.fix_block_base(blks[:2].collapse()).total_length()

    params_wrap = copy.deepcopy(params)
    params_wrap["mw_offset"] = (offset_ticks + unit_ticks) / freq
    blockseq_wrap, _, _, _ = _build_spodmr_blockseq(xdata, params_wrap)
    assert blockseq_wrap.equivalent(blockseq_ofs)

    params_adv = copy.deepcopy(params)
    params_adv["mw_offset"] = -offset_ticks / freq
    blockseq_adv, _, _, _ = _build_spodmr_blockseq(xdata, params_adv)
    adv_patterns = _pattern_map(blockseq_adv)
    mw_changed_adv = False
    mw_diff_from_offset = False
    for ch, p_ref in ref_patterns.items():
        p_adv = adv_patterns[ch]
        if isinstance(ch, str) and ch.startswith("mw"):
            mw_changed_adv |= not np.array_equal(p_ref, p_adv)
            mw_diff_from_offset |= not np.array_equal(ofs_patterns[ch], p_adv)
        else:
            assert np.array_equal(p_ref, p_adv)
    assert mw_changed_adv
    assert mw_diff_from_offset


def test_spodmr(server, spodmr, server_conf, spodmr_conf):
    poll_timeout_ms = spodmr_conf["poll_timeout_ms"]

    spodmr.wait()

    assert get_some(spodmr.get_status, poll_timeout_ms).state == BinaryState.IDLE
    for m in (
        "rabi",
        "fid",
        "spinecho",
        "trse",
        "cp",
        "cpmg",
        "xy4",
        "xy8",
        "xy16",
        "180train",
        "se90sweep",
        "spinlock",
        "xy8cl",
        "xy8cl1flip",
        "ddgate",
    ):
        print(m)
        params = spodmr.get_param_dict(m)
        assert "mw_offset" in params
        params["num"].set(2)  # small num for quick test
        params["accum_window"].set(1e-4)  # small window for quick test
        assert spodmr.validate(params, m)
        assert spodmr.start(params, m)
        assert expect_spodmr(spodmr, params["num"].value(), poll_timeout_ms)
        data = get_some(spodmr.get_data, poll_timeout_ms)
        assert spodmr.stop()
        if m == "rabi":
            save_load_test(SPODMRIO(), data)

    for m in ("cpN", "cpmgN", "xy4N", "xy8N", "xy16N", "xy8clNflip", "ddgateN"):
        params = spodmr.get_param_dict(m)
        assert "mw_offset" in params
        params["Nnum"].set(3)  # small num for quick test
        params["accum_window"].set(1e-4)  # small window for quick test
        assert spodmr.validate(params, m)
        assert spodmr.start(params, m)
        assert expect_spodmr(spodmr, params["Nnum"].value(), poll_timeout_ms)
        assert spodmr.stop()
