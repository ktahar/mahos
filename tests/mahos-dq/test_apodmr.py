#!/usr/bin/env python3

"""
Tests for mahos_dq.meas.apodmr.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np

from mahos.msgs.common_msgs import BinaryState
from mahos_dq.meas.apodmr import APODMRClient
from mahos_dq.meas.apodmr_io import APODMRIO
from mahos_dq.meas.apodmr_worker import APODMRBlockBuilder, APODMRDataOperator
from mahos_dq.msgs.apodmr_msgs import APODMRData
from mahos_dq.meas.podmr_generator.generator import make_generators
from mahos_dq.meas.podmr_generator import generator_kernel as K
from util import expect_value, get_some, save_load_test
from fixtures import ctx, gconf, server, apodmr, server_conf, apodmr_conf


def expect_apodmr(cli: APODMRClient, num: int, poll_timeout_ms):
    def get():
        data = cli.get_data()
        if data is not None and data.data0 is not None:
            return len(data.data0)
        return None

    return expect_value(get, num, poll_timeout_ms, trials=500)


def _apodmr_params() -> dict:
    return {
        "base_width": 320e-9,
        "laser_delay": 200e-9,
        "laser_width": 3e-6,
        "mw_delay": 1e-6,
        "trigger_width": 20e-9,
        "init_delay": 0.0,
        "final_delay": 5e-6,
        "enable_reduce": False,
        "partial": -1,
        "start": 100e-9,
        "num": 2,
        "step": 100e-9,
        "log": False,
        "invert_sweep": False,
        "divide_block": False,
        "roi_head": 100e-9,
        "roi_tail": 50e-9,
        "pd_rate": 500e3,
        "sweeps_per_record": 2,
        "shots_per_point": 1,
        "pulse": {},
        "plot": {
            "plotmode": "data01",
            "taumode": "raw",
            "logX": False,
            "logY": False,
            "sigdelay": 50e-9,
            "sigwidth": 100e-9,
            "refdelay": 150e-9,
            "refwidth": 100e-9,
            "refmode": "ignore",
            "refaverage": False,
            "flipY": False,
        },
    }


def test_apodmr_builder_inserts_trigger_before_each_laser():
    params = _apodmr_params()
    params["shots_per_point"] = 3
    xdata = np.array([100e-9, 200e-9])
    generators = make_generators()
    blocks, freq, common_pulses = generators["rabi"].generate_raw_blocks(xdata, params)
    unit_lengths = [
        blks[i].total_length() + blks[i + 1].total_length()
        for blks in blocks
        for i in range(0, len(blks), 2)
    ]
    builder = APODMRBlockBuilder(
        minimum_block_length=1000,
        block_base=4,
        mw_modes=(0,),
        iq_amplitude=0.0,
        channel_remap=None,
    )
    built, laser_timing, trigger_timing, trace_length_ticks = builder.build_blocks(
        blocks, freq, common_pulses, params, num_mw=1
    )
    base_width, _laser_delay, laser_width, _mw_delay, _tw, init_delay, final_delay = common_pulses
    expected_init_length = K.offset_base_inc(
        max(init_delay + laser_width, builder.minimum_block_length), base_width
    )
    expected_final_length = K.offset_base_inc(
        max(final_delay + laser_width, builder.minimum_block_length), base_width
    )

    trigger = built.decode_digital("trigger")
    for t in trigger_timing:
        assert trigger[t]
    assert built[0].name == "INIT"
    assert built[-1].name == "FINAL"
    assert built[0].total_length() == expected_init_length
    assert built[-1].total_length() == expected_final_length
    assert {"laser", "sync", "mw_i", "mw_q"}.issubset(built[0].digital_channels())
    assert {"sync", "mw_i", "mw_q"}.issubset(built[-1].digital_channels())
    assert "laser" not in built[-1].digital_channels()
    assert len(laser_timing) == len(trigger_timing) == 4
    assert all(
        lt - tt == round(params["roi_head"] * freq) for lt, tt in zip(laser_timing, trigger_timing)
    )
    assert [blk.total_length() for blk in built[1:-1]] == [
        L * params["shots_per_point"] for L in unit_lengths
    ]
    assert [blk.Nrep for blk in built[1:-1]] == [params["shots_per_point"]] * len(unit_lengths)
    assert trace_length_ticks == round(
        (params["roi_head"] + params["laser_width"] + params["roi_tail"]) * freq
    )


def test_apodmr_analyze_rejects_out_of_range_markers():
    data = APODMRData(_apodmr_params(), "rabi")
    data.raw_data = np.zeros((1, 4, 6), dtype=np.float64)
    data.marker_indices = np.array([0, 2, 3, 10], dtype=np.int64)
    op = APODMRDataOperator()

    assert op._analysis_error(data) is not None
    assert op.analyze_with_error(data) is not None
    assert op.analyze(data) is False


def test_apodmr(server, apodmr, server_conf, apodmr_conf):
    poll_timeout_ms = apodmr_conf["poll_timeout_ms"]

    apodmr.wait()

    assert get_some(apodmr.get_status, poll_timeout_ms).state == BinaryState.IDLE

    params = apodmr.get_param_dict("rabi")
    assert "head" not in params["plot"]["taumode"].options()
    params["num"].set(2)
    params["sweeps"].set(4)
    params["sweeps_per_record"].set(2)
    params["shots_per_point"].set(2)
    params["plot"]["sigdelay"].set(0.0)
    params["plot"]["sigwidth"].set(1e-9)
    params["plot"]["refdelay"].set(1e-9)
    params["plot"]["refwidth"].set(1e-9)
    assert apodmr.validate(params, "rabi")
    assert apodmr.start(params, "rabi")
    assert expect_apodmr(apodmr, params["num"].value(), poll_timeout_ms)
    assert expect_value(apodmr.get_state, BinaryState.IDLE, poll_timeout_ms, trials=500)

    data = get_some(apodmr.get_data, poll_timeout_ms)
    assert data is not None
    assert data.raw_data is not None
    assert data.raw_data.shape[0] == 2
    assert int(data.sweeps()) == 4
    assert int(data.raw_data.shape[0] * data.get_sweeps_per_record()) == 4
    assert data.get_samples_per_trace() == data.raw_data.shape[2]
    assert data.marker_indices is not None
    assert data.marker_indices.shape == (4,)
    assert np.isclose(data.trace_laser_timing, params["roi_head"].value())
    assert np.isclose(data.laser_timing[0] - data.trigger_timing[0], params["roi_head"].value())
    save_load_test(APODMRIO(), data)
