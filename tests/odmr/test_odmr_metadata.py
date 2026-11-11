"""
Tests for ODMR instrument metadata and configured sample counts.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from copy import deepcopy
import logging

import numpy as np
import pytest

from mahos.msgs.inst.pg_msgs import Blocks, PulsePattern
from mahos_dq.meas.odmr_io import ODMRIO
from mahos.inst.channel_selection import pd_selections
from mahos_dq.meas.odmr_pd import configure_analog_pds, configure_trace_pds
from mahos_dq.meas.odmr_pg import ODMRPGMixin
from mahos_dq.inst.overlay.odmr_sweeper import ODMRSweeperCommandBase, ODMRSweeperPG
from mahos_dq.msgs.odmr_msgs import ODMRData
from shared.util import save_load_test


def _params():
    return {
        "start": 2.7e9,
        "stop": 2.9e9,
        "num": 2,
        "power": 0.0,
        "background": False,
        "timing": {
            "time_window": 21e-9,
            "laser_delay": 6e-9,
            "laser_width": 8e-9,
            "mw_delay": 20e-9,
            "mw_width": 3e-9,
            "trigger_width": 2e-9,
            "burst_num": 3,
            "roi_head": 4e-9,
            "roi_tail": 8e-9,
            "sig_delay": 0.0,
            "sig_width": 2e-9,
            "ref_delay": 1e-9,
            "ref_width": 2e-9,
            "refmode": "divide",
        },
        "pd": {"rate": 1e9, "eos_deadtime": 2e-9},
    }


class _PD:
    def configure(self, params, label):
        self.params = params
        return True


def _sweeper(conf, *, analog=True, trace=False, spectrum=False, offsets=(0, 4)):
    sweeper = ODMRPGMixin()
    sweeper.conf = conf
    sweeper.pd_names = conf.get("pd_names", ["pd0", "pd1"])
    sweeper.pd_channel_selection = pd_selections(conf, sweeper.pd_names)
    sweeper._pd_analog = analog
    sweeper._pd_trace = trace
    sweeper._pd_spectrum = spectrum
    sweeper.pulse_pattern = PulsePattern(Blocks([]), np.float64(1e9))
    # The metadata path only needs the PG's get() readbacks.
    sweeper.pg = {"length": np.int64(100), "offsets": offsets}
    return sweeper


@pytest.mark.parametrize(
    "analog,trace,spectrum,label,mode,oversample,samples_per_trace",
    [
        (False, False, False, "cw", "counter", None, None),
        (False, False, False, "pulse", "counter", None, None),
        (True, False, False, "cw", "analog_integrated", 21, None),
        (True, False, True, "pulse", "analog_integrated", 12, None),
        (True, True, True, "cw", "analog_integrated", 12, None),
        (True, True, False, "pulse", "analog_trace", 1, 20),
        (True, True, True, "pulse", "analog_trace", 1, 28),
    ],
)
def test_metadata_matches_configured_acquisition(
    analog, trace, spectrum, label, mode, oversample, samples_per_trace
):
    params = _params()
    conf = {
        "pd_names": ["detector"],
        "pd_channel_selection": {"detector": [2]},
        "pd_segment_granularity": 16,
        "pd_segment_offset": 4,
        "pg_freq_pulse": 1e9,
    }
    if not analog:
        conf["pd_channel_selection"] = {}
    sweeper = _sweeper(
        conf,
        analog=analog,
        trace=trace,
        spectrum=spectrum,
        offsets=[np.int64(0), np.int64(4)],
    )
    metadata = sweeper._make_instrument_params(params, label)
    assert metadata["pd_names"] == ["detector"]
    assert metadata["pd_channel_selection"] == conf["pd_channel_selection"]
    assert metadata["pd_mode"] == mode
    assert metadata["pg_freq"] == 1e9
    assert metadata["length"] == 100
    assert metadata["offsets"] == [0, 4]
    assert metadata.get("oversample") == oversample
    assert metadata.get("samples_per_trace") == samples_per_trace

    if analog:
        pd = _PD()
        args = (
            None,
            [pd],
            sweeper.pd_names,
            sweeper.pd_channel_selection,
            "gate",
            params,
            conf,
            spectrum,
            2,
            0,
            None,
            logging.getLogger(),
        )
        if mode == "analog_trace":
            assert configure_trace_pds(*args) == samples_per_trace
            assert pd.params["block_samples"] == samples_per_trace
        else:
            assert configure_analog_pds(*args)
        assert pd.params["oversample"] == oversample
        assert pd.params["channel_selection"] == [2]

    data = ODMRData(deepcopy(params), label)
    data.params["instrument"] = metadata
    data.data = np.ones((2, 1))
    assert data.can_resume(params, label)
    assert not data.can_resume({**params, "power": 1.0}, label)
    save_load_test(ODMRIO(), data)


def test_metadata_is_detached_and_normalizes_zero_offsets():
    names = ["pd0", "pd1"]
    selections = {"pd0": [0, 2], "pd1": None}
    offsets = [0, 0]
    sweeper = _sweeper(
        {"pd_names": names, "pd_channel_selection": selections},
        offsets=offsets,
    )
    metadata = sweeper._make_instrument_params(_params(), "cw")
    names.append("pd2")
    selections["pd0"].append(3)
    sweeper.pd_channel_selection["pd0"].append(3)
    offsets[0] = 4
    assert metadata["pd_names"] == ["pd0", "pd1"]
    assert metadata["pd_channel_selection"] == {"pd0": [0, 2], "pd1": None}
    assert metadata["offsets"] == []


@pytest.mark.parametrize("overlay_type", [ODMRSweeperCommandBase, ODMRSweeperPG])
def test_unconfigured_overlays_have_empty_metadata(overlay_type):
    overlay = overlay_type.__new__(overlay_type)
    overlay._closed = True
    overlay.pulse_pattern = None
    assert overlay.get("instrument_params") == {}
