"""
Exercise latest preview delivery through real Qt subscription threads.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import uuid

import pytest

from shared.transport import transport_contexts as transport_contexts
from mahos.gui.pulse_monitor_client import QPulseClient
from mahos.gui.awg_monitor_client import QAWGClient
from mahos.msgs.inst.pg_msgs import PulsePattern, Blocks
from mahos.msgs.inst.awg_msgs import AWGWaveform
from mahos.node.transport import SnapshotService
from mahos.node.transport.latest import LatestPublisher
from mahos.node.log import DummyLogger


@pytest.mark.parametrize("topic", ["pulse", "wave"])
def test_latest_preview_qt(topic, transport_contexts, qtbot):
    server, client = transport_contexts
    suffix = uuid.uuid4().hex
    conf = {
        topic + "_transport": "latest",
        "pub_endpoint": f"inproc://qt-preview-pub-{suffix}",
        "sync_endpoint": f"inproc://qt-preview-sync-{suffix}",
    }
    service = SnapshotService(server, conf["sync_endpoint"], DummyLogger())

    pub = LatestPublisher(server, conf["pub_endpoint"], topic, service)
    data = (
        PulsePattern(Blocks(), 1e9) if topic == "pulse" else AWGWaveform({}, {}, 1e9, {}, 0, 0, 0)
    )
    pub.publish(data)
    cls = QPulseClient if topic == "pulse" else QAWGClient
    qcli = cls({"localhost": {"preview": conf}}, "localhost::preview", context=client)
    received = []
    signal = qcli.pulseUpdated if topic == "pulse" else qcli.awgUpdated
    getter = qcli.get_pulse if topic == "pulse" else qcli.get_awg
    signal.connect(received.append)
    try:

        def arrived():
            pub.publish(data)
            return len(received) == 1

        qtbot.waitUntil(arrived)
        assert getter().ident == data.ident
        for _ in range(5):
            pub.publish(data)
            qtbot.wait(20)
        assert len(received) == 1
        pub = LatestPublisher(server, conf["pub_endpoint"], topic, service)

        def restarted():
            pub.publish(data)
            return len(received) == 2

        qtbot.waitUntil(restarted)
        assert getter() is received[-1]
    finally:
        qcli.close()
