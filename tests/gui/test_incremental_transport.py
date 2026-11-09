"""
Exercise real measurement nodes and Python/Qt clients with incremental transport.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from mahos_dq.gui.apodmr_client import QAPODMRClient
from mahos_dq.gui.odmr_client import QODMRClient
from mahos_dq.gui.spodmr_client import QSPODMRClient


@pytest.fixture
def measurement(request, gconf, server, sync_endpoint):
    name, partial = request.param
    gconf["localhost"][name].update(
        data_transport="incremental",
        sync_endpoint=sync_endpoint,
        pub_interval_sec=0.05,
    )
    return name, partial, request.getfixturevalue(name)


@pytest.mark.parametrize(
    "measurement",
    [
        ("odmr", None),
        ("spodmr", -1),
        ("spodmr", 0),
        ("spodmr", 1),
        ("spodmr", 2),
        ("apodmr", 0),
        ("apodmr", 1),
        ("apodmr", 3),
    ],
    indirect=True,
)
def test_measurement_clients(measurement, gconf, qtbot):
    name, partial, cli = measurement
    qtbot.waitUntil(lambda: cli.get_status() is not None, timeout=10000)
    method = "cw" if name == "odmr" else "rabi"
    attrs = ("data", "bg_data") if name == "odmr" else ("data0", "data1")
    if name == "apodmr":
        attrs = ("raw_data", "signal_history", "reference_history")
    active_attr = "data1" if name == "spodmr" and partial == 1 else attrs[0]
    params = cli.get_param_dict(method)
    params["num"].set(10 if name == "odmr" else 2)
    if name == "spodmr":
        params["accum_window"].set(1e-4)
        params["partial"].set(partial)
    if name == "apodmr":
        params["max_records"].set(partial)
    assert cli.start(params, method)
    qtbot.waitUntil(
        lambda: cli.get_data() is not None and getattr(cli.get_data(), active_attr) is not None,
        timeout=15000,
    )
    if name == "apodmr":
        initial_count = cli.get_data().records
        qtbot.waitUntil(lambda: cli.get_data().records >= initial_count + 5, timeout=15000)
    assert cli.stop()
    qtbot.waitUntil(lambda: not cli.get_data().running, timeout=10000)
    expected = cli.get_data()
    # Both clients join after acquisition has finished.
    late = type(cli)(gconf, f"localhost::{name}")
    qtype = {"odmr": QODMRClient, "spodmr": QSPODMRClient, "apodmr": QAPODMRClient}[name]
    qcli = qtype(gconf, f"localhost::{name}")
    try:
        qtbot.waitUntil(
            lambda: all(
                c.get_data() is not None and c.get_data().ident == expected.ident
                for c in (late, qcli)
            ),
            timeout=10000,
        )
        for client in (late, qcli):
            assert type(client.get_data()) is type(expected)
            assert not client.get_data().running
            for attr in attrs:
                np.testing.assert_equal(getattr(client.get_data(), attr), getattr(expected, attr))
        # All clients receive a new measurement identifier and populated data after restart.
        assert cli.start(params, method)
        qtbot.waitUntil(
            lambda: all(
                c.get_data().ident != expected.ident
                and getattr(c.get_data(), active_attr) is not None
                for c in (cli, late, qcli)
            ),
            timeout=15000,
        )
        assert cli.stop()
    finally:
        late.close()
        qcli.close()


@pytest.mark.parametrize("standalone", [False, True])
def test_trace_clients(standalone, ctx, gconf, server, sync_endpoint, qtbot):
    from mahos.node.node import start_node_proc
    from mahos.msgs.common_msgs import BinaryState
    from mahos_dq.meas.confocal import Confocal, ConfocalClient, TraceNode, TraceNodeClient
    from mahos_dq.gui.confocal_client import QTracerClient, QTraceNodeClient
    from mahos_dq.msgs.confocal_msgs import ConfocalState
    from shared.fixtures import stop_proc

    conf = gconf["localhost"]["confocal"]
    conf.update(data_transport="incremental", sync_endpoint=sync_endpoint)
    conf["tracer"]["size"] = 10
    node, client, qtclient = (
        (TraceNode, TraceNodeClient, QTraceNodeClient)
        if standalone
        else (Confocal, ConfocalClient, QTracerClient)
    )
    proc, shutdown = start_node_proc(ctx, node, gconf, "localhost::confocal")
    cli = client(gconf, "localhost::confocal")
    late = qcli = None
    try:
        qtbot.waitUntil(lambda: cli.get_status() is not None, timeout=10000)
        assert cli.change_state(BinaryState.ACTIVE if standalone else ConfocalState.INTERACT)
        qtbot.waitUntil(
            lambda: cli.get_trace() is not None and min(cli.get_trace().sample_counts) > 30,
            timeout=10000,
        )
        assert cli.pause_trace()
        qtbot.wait(200)
        expected = cli.get_trace()
        late = client(gconf, "localhost::confocal")
        qcli = qtclient(gconf, "localhost::confocal")
        received = []
        qcli.traceUpdated.connect(received.append)
        qtbot.waitUntil(lambda: late.get_trace() is not None and bool(received), timeout=10000)
        for trace in (late.get_trace(), received[-1]):
            np.testing.assert_equal(trace.traces, expected.traces)
            np.testing.assert_equal(trace.stamps, expected.stamps)
        assert cli.clear_trace()
        assert cli.resume_trace()
        qtbot.waitUntil(
            lambda: cli.get_trace().generation == 1 and received[-1].generation == 1, timeout=10000
        )
        assert cli.change_state(BinaryState.IDLE if standalone else ConfocalState.IDLE)
    finally:
        if late is not None:
            late.close()
        if qcli is not None:
            qcli.close()
        cli.close()
        stop_proc(proc, shutdown)
