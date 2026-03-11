#!/usr/bin/env python3

"""
Tests for mahos_dq.msgs.apodmr_msgs.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np

from mahos_dq.msgs.apodmr_msgs import APODMRData
from mahos_dq.meas.apodmr_io import APODMRIO
from util import save_load_test


def make_data(num_pattern: int, plotmode: str, *, partial: int = -1) -> APODMRData:
    params = {
        "num_pattern": num_pattern,
        "partial": partial,
        "start": 1.0e-9,
        "num": 2,
        "step": 1.0e-9,
        "log": False,
        "invert_sweep": False,
        "roi_head": 4.0e-9,
        "roi_tail": 2.0e-9,
        "trigger_width": 2.0e-9,
        "sweeps_per_record": 2,
        "pulse": {},
        "plot": {
            "plotmode": plotmode,
            "taumode": "raw",
            "refmode": "ignore",
            "refaverage": False,
            "flipY": False,
        },
        "instrument": {
            "tbin": 2.0e-9,
            "trange": 12.0e-9,
            "samples_per_trace": 6,
            "pg_freq": 2.0e9,
            "length": 100,
            "pd_rate": 500e6,
        },
    }
    data = APODMRData(params, "rabi")
    data.trace_laser_timing = params["roi_head"]
    data.trigger_timing = np.arange(num_pattern * params["num"]) * 10.0e-9
    data.laser_timing = data.trigger_timing + params["roi_head"]
    return data


def set_pattern_data(data: APODMRData, signals: list[np.ndarray], refs: list[np.ndarray]):
    for i, (s, r) in enumerate(zip(signals, refs)):
        data.set_data(i, s)
        data.set_data_ref(i, r)


def test_apodmr_raw_xdata_is_trigger_local():
    data = make_data(2, "data01")
    x = data.get_raw_xdata()
    assert np.array_equal(x, np.arange(6) * 2.0e-9)


def test_apodmr_complementary_n2_diff():
    data = make_data(2, "diff")
    set_pattern_data(
        data,
        [np.array([5.0, 7.0]), np.array([1.0, 2.0])],
        [np.array([10.0, 10.0]), np.array([10.0, 10.0])],
    )

    y, y1 = data.get_ydata()
    assert y1 is None
    assert np.array_equal(y, np.array([4.0, 5.0]))


def test_apodmr_complementary_n4_concatenate():
    data = make_data(4, "concatenate")
    set_pattern_data(
        data,
        [
            np.array([10.0, 20.0]),
            np.array([1.0, 2.0]),
            np.array([3.0, 4.0]),
            np.array([5.0, 6.0]),
        ],
        [
            np.array([100.0, 200.0]),
            np.array([10.0, 20.0]),
            np.array([30.0, 40.0]),
            np.array([50.0, 60.0]),
        ],
    )

    y, y1 = data.get_ydata()
    assert y1 is None
    assert np.array_equal(y, np.array([10.0, 1.0, 3.0, 5.0, 20.0, 2.0, 4.0, 6.0]))


def test_apodmr_save_load_roundtrip():
    data = make_data(2, "data01")
    data.raw_data = np.arange(24, dtype=np.float64).reshape(1, 4, 6)
    assert data.records() == 1
    assert data.sweeps() == 2
    assert np.isclose(data.measurement_time(), 100e-9)
    set_pattern_data(
        data,
        [np.array([5.0, 7.0]), np.array([1.0, 2.0])],
        [np.array([10.0, 10.0]), np.array([10.0, 10.0])],
    )

    save_load_test(APODMRIO(), data)
