#!/usr/bin/env python3

"""
Tests for Recorder.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.meas.recorder import RecorderClient, RecorderIO
from mahos.msgs.common_msgs import BinaryState
from util import get_some, expect_value, save_load_test
from fixtures import ctx, gconf, server, recorder, server_conf, recorder_conf


def expect_recorder(cli: RecorderClient, poll_timeout_ms, inst: str, length: int = 3):
    def get():
        data = cli.get_data()
        if data is not None and data.has_data():
            return len(data.get_ydata(inst)) >= length
        else:
            return None

    return expect_value(get, True, poll_timeout_ms, trials=500)


def test_recorder(server, recorder, server_conf, recorder_conf):
    poll_timeout_ms = recorder_conf["poll_timeout_ms"]

    recorder.wait()

    assert get_some(recorder.get_status, poll_timeout_ms).state == BinaryState.IDLE

    params = recorder.get_param_dict("mix")
    assert recorder.change_state(BinaryState.ACTIVE, params, "mix")
    assert expect_recorder(recorder, poll_timeout_ms, "dmm0_v1")
    data = get_some(recorder.get_data, poll_timeout_ms)
    assert recorder.change_state(BinaryState.IDLE)

    save_load_test(RecorderIO(), data)


def test_recorder_channel_key_and_unit_conf(server, recorder, server_conf, recorder_conf):
    poll_timeout_ms = recorder_conf["poll_timeout_ms"]

    recorder.wait()

    assert get_some(recorder.get_status, poll_timeout_ms).state == BinaryState.IDLE

    params = recorder.get_param_dict("key_unit")
    assert recorder.change_state(BinaryState.ACTIVE, params, "key_unit")
    assert expect_recorder(recorder, poll_timeout_ms, "dmm0_v1_Volt")
    data = get_some(recorder.get_data, poll_timeout_ms)
    assert recorder.change_state(BinaryState.IDLE)

    assert data.get_unit("dmm0_v1_Volt") == "Volt"
    assert data.get_unit("dmm1_ready") == ""
    ready = data.get_ydata("dmm1_ready")
    assert ready.dtype.kind == "b"
    assert ready.all()

    channels = data.params["channels"]
    assert channels["dmm0_v1_Volt"]["inst"] == "dmm0"
    assert channels["dmm0_v1_Volt"]["label"] == "ch1_dcv"
    assert channels["dmm0_v1_Volt"]["key"] == "data"
    assert channels["dmm0_v1_Volt"]["unit"] == "Volt"
    assert channels["dmm1_ready"]["inst"] == "dmm1"
    assert channels["dmm1_ready"]["label"] == "ch1_dcv"
    assert channels["dmm1_ready"]["key"] == "opc"
    assert channels["dmm1_ready"]["unit"] == ""
