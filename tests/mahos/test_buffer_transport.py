"""
Versioned buffer tracking, recovery, ownership, and real socket integration tests.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import copy
import time
import uuid
from types import SimpleNamespace

import numpy as np
import pytest
import zmq

from mahos.msgs.common_meas_msgs import BasicMeasData, Buffer, TrackedBuffer
from mahos.node.buffer_transport import (
    BATCH_SIZE,
    TOPIC,
    BufferPublisher,
    BufferSubscriber,
    response,
)
from mahos.node.comm import Context, serialize_pickle, deserialize
from mahos.node.data_transport import (
    ArrayPolicy,
    IncrementalPublisher,
    IncrementalSubscriber,
    SnapshotService,
    TransportConfig,
)
from mahos.node.log import DummyLogger


def dataset(value):
    data = BasicMeasData()
    data.values = np.array([value], dtype=float)
    return data


@pytest.fixture
def transport():
    zctx = zmq.Context()
    server = Context(zctx, poll_timeout_ms=1)
    client = Context(zctx, poll_timeout_ms=1)
    suffix = uuid.uuid4().hex
    conf = {
        "buffer_transport": "versioned",
        "pub_endpoint": f"inproc://buffer-pub-{suffix}",
        "sync_endpoint": f"inproc://buffer-sync-{suffix}",
    }
    service = SnapshotService(zctx, conf["sync_endpoint"], ("initial", 0, None), DummyLogger())
    server.add_close_service(service)
    pub = BufferPublisher(server, conf["pub_endpoint"], service)
    yield server, client, conf, service, pub
    client.close()
    server.close()
    zctx.term()


def pump(client, condition, publish=None):
    deadline = time.monotonic() + 3
    while not condition() and time.monotonic() < deadline:
        if publish:
            publish()
        client.poll()
    assert condition()


def values(buffer):
    return [data.values[0] for _, data in buffer]


def test_tracking_list_operations():
    buffer = TrackedBuffer([("same", dataset(1)), ("same", dataset(2))])
    original = buffer.entry_versions()
    assert original[0][0] != original[1][0]
    buffer.touch(-1)
    assert buffer.entry_versions()[1][1] == 1
    buffer.reverse()
    assert buffer.entry_versions()[0][0] == original[1][0]
    buffer.sort(key=lambda item: item[1].values[0])
    assert buffer.entry_versions()[0][0] == original[0][0]
    removed = buffer.pop(0)
    buffer.insert(0, removed)
    assert buffer.entry_versions()[0][0] != original[0][0]
    buffer[1:] = ((name, dataset(value)) for name, value in (("third", 3), ("fourth", 4)))
    assert values(buffer) == [1, 3, 4]
    buffer += [("fifth", dataset(5))]
    buffer *= 2
    assert len({entry[0] for entry in buffer.entry_versions()}) == 8
    cloned = copy.copy(buffer)
    cloned.touch(0)
    assert cloned.epoch != buffer.epoch
    assert cloned.entry_versions()[0] != buffer.entry_versions()[0]
    del buffer[::2]
    assert len(buffer.entry_versions()) == 4
    buffer.clear()
    assert buffer.entry_versions() == ()


def test_configuration():
    assert TransportConfig({}).buffer_mode == "pubsub"
    assert TransportConfig({"buffer_transport": "versioned", "sync_endpoint": "x"}).endpoint == "x"
    for conf in ({"buffer_transport": "other"}, {"buffer_transport": "versioned"}):
        with pytest.raises((ValueError, KeyError)):
            TransportConfig(conf)


def test_only_changed_entries_and_private_copies(transport, monkeypatch):
    server, client, conf, service, pub = transport
    calls = []
    original = service._serve_batch

    def record(router, requests):
        calls.extend(args[1][1] for args in requests.values() if args[0] == "buffer")
        return original(router, requests)

    monkeypatch.setattr(service, "_serve_batch", record)
    received = []
    sub = BufferSubscriber(client, conf, received.append)
    buffer = TrackedBuffer([("duplicate", dataset(1)), ("duplicate", dataset(2))])
    publish = lambda: pub.publish(buffer)
    pump(client, lambda: len(received) == 1, publish)
    assert type(received[0]) is Buffer
    assert values(received[0]) == [1, 2]
    assert sum(map(len, calls)) == 2
    received[0][0][1].values[:] = 99
    for _ in range(20):
        publish()
        client.poll()
    assert len(received) == 1
    assert sum(map(len, calls)) == 2
    buffer.append(("new", dataset(3)))
    pump(client, lambda: len(received) == 2, publish)
    assert values(received[-1]) == [1, 2, 3]
    assert values(received[0]) == [99, 2]
    assert sum(map(len, calls)) == 3
    buffer[1][1].values[:] = 4
    buffer.touch(1)
    pump(client, lambda: len(received) == 3, publish)
    assert values(received[-1]) == [1, 4, 3]
    assert sum(map(len, calls)) == 4
    buffer.reverse()
    pump(client, lambda: len(received) == 4, publish)
    assert values(received[-1]) == [3, 4, 1]
    assert sum(map(len, calls)) == 4
    buffer.pop()
    pump(client, lambda: len(received) == 5, publish)
    assert len(sub.cache) == 2
    buffer.clear()
    pump(client, lambda: len(received) == 6, publish)
    assert received[-1] == []
    assert not sub.cache


def test_batches_late_join_and_replaced_buffer(transport):
    _, client, conf, _, pub = transport
    buffer = TrackedBuffer([("same", dataset(i)) for i in range(BATCH_SIZE * 2 + 1)])
    pub.publish(buffer)
    received = []
    sub = BufferSubscriber(client, conf, received.append)
    pump(client, lambda: bool(received), lambda: pub.publish(buffer))
    assert len(received) == 1
    assert values(received[0]) == list(range(len(buffer)))
    buffer = TrackedBuffer([("same", dataset(-1))])
    pump(client, lambda: len(received) == 2, lambda: pub.publish(buffer))
    assert values(received[-1]) == [-1]
    assert len(sub.cache) == 1


def test_stale_versions_and_immutable_publication(transport):
    _, client, conf, service, pub = transport
    buffer = TrackedBuffer([("x", dataset(1))])
    pub.publish(buffer)
    old_manifest = BufferPublisher.make_manifest(buffer)
    key = old_manifest[3][0][:2]
    buffer[0][1].values[:] = 2
    buffer.touch(0)
    # The committed copy cannot be mutated by later node work.
    assert response("id", buffer.epoch, [key], service._buffer_latest)[5][0][2].values[0] == 1
    pub.publish(buffer)
    dealer = client.zmq_context().socket(zmq.DEALER)
    dealer.setsockopt(zmq.LINGER, 0)
    dealer.connect(conf["sync_endpoint"])
    try:
        dealer.send(serialize_pickle(("buffer", 1, "id", buffer.epoch, [key])))
        assert dealer.poll(3000)
        result = deserialize(dealer.recv(), None)
        assert result[3] == "stale"
        assert result[4] == BufferPublisher.make_manifest(buffer)
        assert result[5] == []
        buffer.clear()
        pub.publish(buffer)
        dealer.send(serialize_pickle(("buffer", 1, "removed", buffer.epoch, [key])))
        assert dealer.poll(3000)
        assert deserialize(dealer.recv(), None)[3] == "stale"
    finally:
        dealer.close()


def test_supersession_delayed_responses_and_validation(transport):
    _, client, conf, _, pub = transport
    received = []
    sub = BufferSubscriber(client, conf, received.append)
    buffer = TrackedBuffer([("x", dataset(1))])
    pub.publish(buffer)
    old_manifest = BufferPublisher.make_manifest(buffer)
    sub.handle_frames([TOPIC, serialize_pickle(old_manifest)])
    key = old_manifest[3][0][:2]
    sub.pending = ("buffer", 1, "old", buffer.epoch, [key])
    old_response = response("old", buffer.epoch, [key], (old_manifest, pub.entries))
    buffer[0][1].values[:] = 2
    buffer.touch(0)
    pub.publish(buffer)
    sub.handle_frames([TOPIC, serialize_pickle(BufferPublisher.make_manifest(buffer))])
    sub._receive([serialize_pickle(old_response)])
    sub.handle_frames([TOPIC, serialize_pickle(old_manifest)])
    assert sub.manifest == BufferPublisher.make_manifest(buffer)
    assert not received and not sub.cache
    new_key = (key[0], 1)
    sub.pending = ("buffer", 1, "new", buffer.epoch, [new_key])
    invalid = (
        1,
        "buffer",
        "new",
        "ok",
        BufferPublisher.make_manifest(buffer),
        [(key[0], 0, dataset(9))],
    )
    with pytest.raises(ValueError):
        sub._receive([serialize_pickle(invalid)])
    assert sub.pending is not None and not sub.cache
    valid = response(
        "new", buffer.epoch, [new_key], (BufferPublisher.make_manifest(buffer), pub.entries)
    )
    sub._receive([serialize_pickle(valid)])
    sub._deliver()
    assert values(received[-1]) == [2]
    sub._receive([serialize_pickle(old_response)])
    assert values(received[-1]) == [2]


def test_combined_endpoint_and_raw_topic_isolation(transport):
    server, client, conf, service, pub = transport
    conf = {**conf, "data_transport": "incremental"}
    live_pub = IncrementalPublisher(
        server, conf["pub_endpoint"], conf["sync_endpoint"], {"a": ArrayPolicy(0)}, service=service
    )
    live, buffers, raw = [], [], []
    IncrementalSubscriber(client, conf, live.append)
    BufferSubscriber(client, conf, buffers.append)
    client.add_sub(conf["pub_endpoint"], b"buffer", raw.append)
    buffer = TrackedBuffer([("x", dataset(1))])

    def publish():
        pub.publish(buffer)
        if not live:
            live_pub.publish(SimpleNamespace(a=np.arange(3)))

    pump(client, lambda: bool(live) and bool(buffers), publish)
    assert not raw
    np.testing.assert_array_equal(live[-1].a, np.arange(3))
    assert values(buffers[-1]) == [1]


def test_stale_response_reconciles_without_mixing(transport):
    _, client, conf, service, pub = transport
    received = []
    sub = BufferSubscriber(client, conf, received.append)
    buffer = TrackedBuffer([("x", dataset(1))])
    pump(client, lambda: bool(received), lambda: pub.publish(buffer))
    buffer.append(("y", dataset(2)))
    pub.publish(buffer)
    sub.handle_frames([TOPIC, serialize_pickle(BufferPublisher.make_manifest(buffer))])
    ident, rev, _ = BufferPublisher.make_manifest(buffer)[3][1]
    sub.pending = ("buffer", 1, "fetch", buffer.epoch, [(ident, rev)])
    buffer[1][1].values[:] = 3
    buffer.touch(1)
    pub.publish(buffer)
    stale = response("fetch", buffer.epoch, [(ident, rev)], service._buffer_latest)
    sub._receive([serialize_pickle(stale)])
    sub._deliver()
    assert len(received) == 1 and values(received[0]) == [1]
    assert sub.manifest == BufferPublisher.make_manifest(buffer)
    pump(client, lambda: len(received) == 2)
    assert values(received[-1]) == [1, 3]


def test_lost_reply_retries_same_request(transport, monkeypatch):
    import mahos.node.buffer_transport as module

    _, client, conf, service, pub = transport
    now = [10.0]
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    requests = []
    original = service._serve_batch

    def drop_first(router, batch):
        requests.extend(batch)
        if len(requests) > 1:
            return original(router, batch)

    monkeypatch.setattr(service, "_serve_batch", drop_first)
    received = []
    sub = BufferSubscriber(client, conf, received.append)
    buffer = TrackedBuffer([("x", dataset(1))])
    pump(client, lambda: bool(requests), lambda: pub.publish(buffer))
    pending = sub.pending
    assert not received
    now[0] += 6.0
    pump(client, lambda: bool(received))
    assert requests[0] == requests[1]
    assert pending[2] == requests[0][1]
    assert len(received) == 1


def test_fit_failure_marks_partial_mutation():
    from mahos.meas.common_meas import BasicMeasNode
    from mahos.msgs.common_meas_msgs import FitReq

    class Data(BasicMeasData):
        def has_data(self):
            return True

    def fit(data, params, label):
        data.fit_data = np.ones(2)
        raise RuntimeError("partial fit")

    buffer = TrackedBuffer([("fit", Data())])
    node = SimpleNamespace(
        buffer=buffer, DATA=Data, fitter=SimpleNamespace(fitd=fit), logger=DummyLogger()
    )
    assert not BasicMeasNode.fit(node, FitReq({}, data_index=0)).success
    assert buffer.entry_versions()[0][1] == 1
    assert buffer[0][1].fit_data is not None


def test_callback_exceptions_propagate(transport):
    _, client, conf, _, _ = transport

    def fail(buffer):
        raise RuntimeError("application handler")

    sub = BufferSubscriber(client, conf, fail)
    with pytest.raises(RuntimeError, match="application handler"):
        sub.handle_frames(
            [TOPIC, serialize_pickle(BufferPublisher.make_manifest(TrackedBuffer()))]
        )
