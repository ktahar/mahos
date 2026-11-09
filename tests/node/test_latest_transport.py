"""
Latest preview transport ownership, retries, and real socket delivery.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import time
import uuid
from types import SimpleNamespace

import pytest

from mahos.node.comm import serialize_pickle
from mahos.node.data_transport import SnapshotService
from mahos.node.latest_transport import LatestPublisher, LatestSubscriber
from mahos.node.log import DummyLogger
from mahos.node.transport_util import TransportConfig


def pump(client, condition, publish=lambda: None):
    deadline = time.monotonic() + 3
    while not condition() and time.monotonic() < deadline:
        publish()
        client.poll()
    assert condition()


@pytest.fixture
def setup(transport_contexts):
    server, client = transport_contexts
    suffix = uuid.uuid4().hex
    conf = dict(
        pulse_transport="latest",
        wave_transport="latest",
        pub_endpoint=f"inproc://latest-pub-{suffix}",
        sync_endpoint=f"inproc://latest-sync-{suffix}",
    )
    service = SnapshotService(
        server.zmq_context(), conf["sync_endpoint"], ("initial", 0, None), DummyLogger()
    )
    server.add_close_service(service)
    return server, client, conf, service


def test_configuration():
    assert not TransportConfig({}).needs_service
    for topic in ("pulse", "wave"):
        with pytest.raises((ValueError, KeyError)):
            TransportConfig({topic + "_transport": "latest"})
        with pytest.raises(ValueError):
            TransportConfig({topic + "_transport": "invalid"})
        assert TransportConfig(
            {topic + "_transport": "latest", "sync_endpoint": "x"}
        ).needs_service


def test_late_join_private_commit_and_restart(setup):
    server, client, conf, service = setup
    pub = LatestPublisher(server, conf["pub_endpoint"], "pulse", service)
    data = SimpleNamespace(ident=uuid.uuid4(), values=[1])
    pub.publish(data)
    data.values.append(2)
    received = []
    sub = LatestSubscriber(client, conf, "pulse", received.append)
    pump(client, lambda: len(received) == 1, lambda: pub.publish(data))
    assert received[0].values == [1]
    cached = service._objects["pulse"]
    for _ in range(10):
        pub.publish(data)
        client.poll()
    assert len(received) == 1
    assert service._objects["pulse"] is cached
    assert cached[2] is not None
    # A new publisher epoch with the same UUID must deliver again.
    replacement = LatestPublisher(server, conf["pub_endpoint"], "pulse", service)
    pump(client, lambda: len(received) == 2, lambda: replacement.publish(data))
    assert received[-1].values == [1, 2]
    assert sub.delivered == replacement.identity


def test_topics_and_update_during_fetch(setup):
    server, client, conf, service = setup
    pulse = LatestPublisher(server, conf["pub_endpoint"], "pulse", service)
    wave = LatestPublisher(server, conf["pub_endpoint"], "wave", service)
    first = SimpleNamespace(ident=uuid.uuid4(), values=[1])
    second = SimpleNamespace(ident=uuid.uuid4(), values=[2])
    pulse.publish(first)
    received, waves = [], []
    sub = LatestSubscriber(client, conf, "pulse", received.append)
    LatestSubscriber(client, conf, "wave", waves.append)
    # The service advances before an old announcement triggers the fetch.
    old = pulse.identity
    pulse.publish(second)
    sub.handle_frames([b"latest_pulse", serialize_pickle((1, old))])
    pump(client, lambda: bool(received) and bool(waves), lambda: wave.publish(first))
    assert received[-1].values == [2]
    assert waves[-1].values == [1]
    assert sub.delivered == pulse.identity


def test_retry_and_obsolete_response(setup):
    server, client, conf, service = setup
    pub = LatestPublisher(server, conf["pub_endpoint"], "pulse", service)
    pub.publish(SimpleNamespace(ident=uuid.uuid4(), values=[1]))
    received = []
    sub = LatestSubscriber(client, conf, "pulse", received.append)
    sub.handle_frames([b"latest_pulse", serialize_pickle((1, pub.identity))])
    sub.poll()
    request = sub.pending
    sub.deadline = 0
    sub.poll()
    # May already have received the real response; otherwise the retry keeps its ID.
    assert sub.pending is None or sub.pending == request
    pump(client, lambda: bool(received))
    sub._receive([serialize_pickle((1, "latest", "obsolete", "pulse", pub.identity, False))])
    assert len(received) == 1


def test_shared_service_with_live_and_buffer(setup):
    import numpy as np
    from mahos.node.data_transport import IncrementalPublisher, IncrementalSubscriber, ArrayPolicy
    from mahos.node.buffer_transport import BufferPublisher, BufferSubscriber
    from mahos.msgs.common_meas_msgs import TrackedBuffer

    server, client, conf, service = setup
    conf.update(data_transport="incremental", buffer_transport="versioned")
    live = IncrementalPublisher(
        server,
        conf["pub_endpoint"],
        conf["sync_endpoint"],
        {"values": ArrayPolicy(0, 0)},
        service=service,
    )
    buffer = BufferPublisher(server, conf["pub_endpoint"], service)
    preview = LatestPublisher(server, conf["pub_endpoint"], "wave", service)
    live_data, buffers, waves = [], [], []
    IncrementalSubscriber(client, conf, live_data.append)
    BufferSubscriber(client, conf, buffers.append)
    LatestSubscriber(client, conf, "wave", waves.append)
    data = SimpleNamespace(ident=uuid.uuid4(), values=np.array([1.0]))
    storage = TrackedBuffer([("one", data)])

    def publish():
        live.publish(data)
        buffer.publish(storage)
        preview.publish(data)

    pump(client, lambda: bool(live_data) and bool(buffers) and bool(waves), publish)
    assert waves[-1].ident == data.ident
    assert buffers[-1][0][1].ident == data.ident
    np.testing.assert_array_equal(live_data[-1].values, data.values)
