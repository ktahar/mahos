"""
Test versioned buffers through real measurement nodes and Python/Qt clients.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from fixtures import ctx, gconf, server, odmr, podmr, spodmr, apodmr, hbt, spectroscopy
from mahos.gui.client import QBasicMeasClient
from mahos.msgs.common_meas_msgs import Buffer
from mahos.node.log import DummyLogger
from mahos.util.io import save_pickle_or_h5
from mahos_dq.msgs.odmr_msgs import ODMRData
from mahos_dq.msgs.podmr_msgs import PODMRData
from mahos_dq.msgs.spodmr_msgs import SPODMRData
from mahos_dq.msgs.apodmr_msgs import APODMRData
from mahos_dq.msgs.hbt_msgs import HBTData
from mahos_dq.msgs.spectroscopy_msgs import SpectroscopyData


@pytest.fixture
def measurement(request, gconf, tmp_path, server):
    name, live = request.param
    gconf["localhost"][name].update(
        buffer_transport="versioned",
        data_transport=live,
        sync_endpoint=f"ipc://{tmp_path}/sync",
        pub_interval_sec=0.05,
    )
    return name, request.getfixturevalue(name)


@pytest.mark.parametrize(
    "measurement",
    [(name, "pubsub") for name in ("odmr", "podmr", "spodmr", "apodmr", "hbt", "spectroscopy")]
    + [(name, "incremental") for name in ("odmr", "spodmr", "apodmr")],
    indirect=True,
)
def test_measurement_buffer_clients(measurement, gconf, qtbot, tmp_path):
    name, cli = measurement
    types = dict(
        odmr=ODMRData,
        podmr=PODMRData,
        spodmr=SPODMRData,
        apodmr=APODMRData,
        hbt=HBTData,
        spectroscopy=SpectroscopyData,
    )
    dtype = types[name]
    data = dtype()
    data.fit_xdata = np.arange(4, dtype=float)
    data.fit_data = np.arange(4, dtype=float) + 1
    filename = str(tmp_path / "buffer.h5")
    assert save_pickle_or_h5(filename, data, dtype, DummyLogger())
    qtbot.waitUntil(lambda: cli.get_status() is not None, timeout=10000)
    assert cli.load_data(filename, to_buffer=True) is not None
    assert cli.load_data(filename, to_buffer=True) is not None
    late = type(cli)(gconf, f"localhost::{name}")
    qcli = QBasicMeasClient(gconf, f"localhost::{name}")
    signals = []
    qcli.bufferUpdated.connect(signals.append)
    clients = (cli, late, qcli)
    try:
        qtbot.waitUntil(
            lambda: all(c.get_buffer() is not None and len(c.get_buffer()) == 2 for c in clients),
            timeout=10000,
        )
        for client in clients:
            buffer = client.get_buffer()
            assert type(buffer) is Buffer
            assert type(buffer[0][1]) is dtype
            assert buffer.file_names()[0] == buffer.file_names()[1]
            np.testing.assert_equal(buffer[0][1].fit_data, data.fit_data)
        retained = qcli.get_buffer()
        # Common fit clearing changes just one buffered entry, preserving old deliveries.
        assert cli.clear_fit(data_index=0)
        qtbot.waitUntil(
            lambda: all(c.get_buffer()[0][1].fit_data is None for c in clients), timeout=10000
        )
        assert retained[0][1].fit_data is not None
        assert qcli.get_buffer()[1][1].fit_data is not None
        count = len(signals)
        qtbot.wait(300)
        assert len(signals) == count
        assert cli.pop_buffer(0) is not None
        qtbot.waitUntil(lambda: all(len(c.get_buffer()) == 1 for c in clients), timeout=10000)
        assert cli.clear_buffer()
        qtbot.waitUntil(lambda: all(len(c.get_buffer()) == 0 for c in clients), timeout=10000)
    finally:
        late.close()
        qcli.close()
