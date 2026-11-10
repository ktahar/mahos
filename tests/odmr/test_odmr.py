#!/usr/bin/env python3

"""
Tests for mahos_dq.meas.odmr.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from copy import deepcopy

import pytest

from mahos_dq.meas.odmr import ODMRClient, ODMRIO
from mahos.msgs.common_msgs import BinaryState
from shared.util import get_some, get_final_data, expect_value, save_load_test


def expect_odmr(cli: ODMRClient, params: dict, poll_timeout_ms):
    def get():
        data = cli.get_data()
        if data is not None and data.data is not None:
            return data.data.shape[0]
        else:
            return None

    v = params["num"]
    return expect_value(get, v, poll_timeout_ms, trials=500)


def test_odmr(server, odmr, odmr_conf, sg_power_bounds):
    poll_timeout_ms = odmr_conf["poll_timeout_ms"]

    odmr.wait()

    params = odmr.get_param_dict("cw")
    params["num"].set(10)
    power = params["power"]
    assert (power.minimum(), power.maximum()) == sg_power_bounds
    assert odmr.get_param_dict("non-existent-name") == None
    assert get_some(odmr.get_status, poll_timeout_ms).state == BinaryState.IDLE

    assert odmr.change_state(BinaryState.ACTIVE, params, "cw")
    assert expect_odmr(odmr, params.unwrap(), poll_timeout_ms)
    data = get_some(odmr.get_data, poll_timeout_ms)

    assert odmr.change_state(BinaryState.IDLE)

    save_load_test(ODMRIO(), data)


@pytest.mark.parametrize("backend", ["direct", "pg_overlay"])
@pytest.mark.parametrize("analog", [False, True])
def test_odmr_instrument_metadata_and_resume(request, backend, analog, server_conf, odmr_conf):
    # Configure the backend before starting the server and measurement fixtures.
    pg = server_conf["instrument"]["pg"]
    pg["class"] = "PulseStreamer_mock"
    pg["conf"]["resource"] = "mock"
    acquisition = {"pd_analog": analog}
    if analog:
        acquisition.update(pd_rate=1e6, pd_channel_selection={"pd0": [0]})
    if backend != "direct":
        conf = dict(acquisition, sg="$sg", pg="$pg", pd0="$pd0", pd1="$pd1", pd_clock="/Dummy")
        if analog:
            conf["clock"] = "$clock"
        server_conf["instrument_overlay"]["odmr_sweeper"] = {
            "module": "mahos_dq.inst.overlay.odmr_sweeper",
            "class": "ODMRSweeperPG",
            "conf": conf,
        }
        odmr_conf["sweeper"] = {"sweeper_name": "odmr_sweeper", "point": True}
        odmr_conf["target"]["servers"] = {"odmr_sweeper": "localhost::server"}
    else:
        odmr_conf["sweeper"].update(acquisition)
        if analog:
            odmr_conf["target"]["servers"]["clock"] = "localhost::server"
    request.getfixturevalue("server")
    cli = request.getfixturevalue("odmr")
    poll_timeout_ms = odmr_conf["poll_timeout_ms"]
    cli.wait()
    params = cli.get_param_dict("cw")
    params["num"].set(3)
    params["sweeps"].set(1)
    assert cli.start(params, "cw")
    data = get_final_data(cli.get_data, poll_timeout_ms)
    assert data is not None
    metadata = deepcopy(data.params["instrument"])
    assert metadata["pd_names"] == ["pd0", "pd1"]
    assert metadata["pd_channel_selection"] == ({"pd0": [0]} if analog else {})
    assert metadata["pd_mode"] == ("analog_integrated" if analog else "counter")
    assert metadata["pg_freq"] == 1e9
    assert metadata["length"] > 0
    assert metadata["offsets"] == []
    if analog:
        assert metadata["oversample"] == round(
            params["timing"]["time_window"].value() * params["pd"]["rate"].value()
        )
    assert "pd_channel_selection" not in data.params
    assert data.can_resume(params.unwrap(), "cw")
    save_load_test(ODMRIO(), data)

    original_sweeps = data.sweeps()
    ident = data.ident
    resume_params = {
        **params.unwrap(),
        "resume": True,
        "ident": ident,
        "sweeps": original_sweeps + 1,
    }
    assert cli.start(resume_params, "cw")
    assert expect_value(
        lambda: cli.get_data().sweeps() > original_sweeps and cli.get_data().is_finalized(),
        True,
        poll_timeout_ms,
    )
    assert cli.stop()
    resumed = get_final_data(cli.get_data, poll_timeout_ms)
    assert resumed.ident == ident
    assert resumed.params["instrument"] == metadata

    # Also exercise resume without supplying a new parameter dictionary.
    assert cli.start()
    assert cli.stop()
    resumed = get_final_data(cli.get_data, poll_timeout_ms)
    assert resumed.ident == ident
    assert resumed.params["instrument"] == metadata
