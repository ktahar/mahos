"""
Incremental transport tests using real in-process ZMQ sockets.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import copy
import pickle
import zlib
import time
import threading
import uuid
from types import SimpleNamespace

import numpy as np
import pytest
import zmq

from mahos.msgs.common_msgs import Message, pickle_proto
from mahos.node.comm import Context, serialize, deserialize
import mahos.node.data_transport as transport_module
from mahos.node.data_transport import (
    ArrayPolicy,
    IncrementalPublisher,
    IncrementalSubscriber,
    TOPIC,
    TransportConfig,
)
from mahos.node.log import DummyLogger


class CompressedData(Message):
    """Data with custom serialization that incremental transport must bypass.

    :ivar a: Growing array.
    :ivar b: Unused optional array.

    """

    def __init__(self):
        self.a = np.ones((2, 1))
        self.b = None

    def serialize(self):
        return zlib.compress(pickle.dumps(self, protocol=pickle_proto))

    @classmethod
    def deserialize(cls, payload):
        return pickle.loads(zlib.decompress(payload))


@pytest.fixture
def transport():
    zctx = zmq.Context()
    server = Context(zctx, poll_timeout_ms=1)
    client = Context(zctx, poll_timeout_ms=1)
    suffix = uuid.uuid4().hex
    conf = {
        "data_transport": "incremental",
        "pub_endpoint": f"inproc://pub-{suffix}",
        "sync_endpoint": f"inproc://sync-{suffix}",
    }
    yield server, client, conf
    client.close()
    server.close()
    zctx.term()


@pytest.fixture
def recovery_clock(monkeypatch):
    """Control recovery deadlines while keeping socket pump timeouts on real time."""

    now = [0.0]
    monkeypatch.setattr(transport_module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    return now


def pump(server, client, condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        server.poll()
        client.poll()
    assert condition()


def publisher(server, conf, tail=0, axis=1):
    return IncrementalPublisher(
        server,
        conf["pub_endpoint"],
        conf["sync_endpoint"],
        {"a": ArrayPolicy(axis, tail), "b": ArrayPolicy(axis, tail)},
    )


@pytest.fixture
def controlled_recovery(transport):
    """Use a test-owned ROUTER to exercise delayed or malformed server responses."""

    server, client, conf = transport
    pub = publisher(server, {**conf, "sync_endpoint": conf["sync_endpoint"] + "-unused"})
    router = server.zmq_context().socket(zmq.ROUTER)
    router.setsockopt(zmq.LINGER, 0)
    router.bind(conf["sync_endpoint"])
    try:
        yield server, client, conf, pub, router
    finally:
        router.close()


def response_frames(response):
    version, request_id, epoch, revision, state = response
    frames = [serialize((version, request_id, epoch, revision, state is not None))]
    if state is not None:
        frames.append(pickle.dumps(state, protocol=pickle_proto))
    return frames


def test_delayed_snapshot_survives_retries(controlled_recovery, monkeypatch):
    server, client, conf, pub, router = controlled_recovery
    now = [0.0]
    monkeypatch.setattr(transport_module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    source = SimpleNamespace(a=np.ones((2, 3)), b=None)
    pub.publish(source)

    def receive_request():
        assert router.poll(1000)
        identity, payload = router.recv_multipart()
        return identity, deserialize(payload, None)

    # Hold the first response while the client crosses multiple retry deadlines.
    sub.poll()
    identity, request = receive_request()
    response = (request[0], request[1], pub.epoch, pub.revision, pub.state)
    for instant in (6.0, 12.0):
        now[0] = instant
        sub.poll()
        assert receive_request() == (identity, request)

    router.send_multipart([identity, *response_frames(response)])
    assert sub.socket.poll(1000)
    sub.poll()
    assert sub.pending is None
    assert len(received) == 1
    np.testing.assert_equal(received[-1].a, source.a)

    # A duplicate of the completed request must not complete a newer request.
    now[0] = 13.0
    sub.poll()
    _, newer = receive_request()
    assert newer[1] != request[1]
    router.send_multipart([identity, *response_frames(response)])
    assert sub.socket.poll(1000)
    sub.poll()
    assert sub.pending == newer[1]
    assert len(received) == 1
    router.send_multipart(
        [identity, *response_frames((newer[0], newer[1], pub.epoch, pub.revision, None))]
    )
    assert sub.socket.poll(1000)
    sub.poll()
    assert sub.pending is None


def test_retry_preserves_arguments_while_live_data_advances(controlled_recovery, monkeypatch):
    server, client, conf, pub, router = controlled_recovery
    now = [0.0]
    monkeypatch.setattr(transport_module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    source = SimpleNamespace(a=np.ones((2, 1)), b=None)
    pub.publish(source)
    sub.poll()
    assert router.poll(1000)
    identity, payload = router.recv_multipart()
    initial = deserialize(payload, None)
    router.send_multipart(
        [identity, *response_frames((initial[0], initial[1], pub.epoch, 1, pub.state))]
    )
    assert sub.socket.poll(1000)
    sub.poll()
    assert sub.revision == 1

    now[0] = 1.0
    sub.poll()
    assert router.poll(1000)
    identity, payload = router.recv_multipart()
    request = deserialize(payload, None)
    assert request[3:] == (1, False)

    # Process a live update without servicing the outstanding version query.
    source.a = np.ones((2, 2))
    pub.publish(source)
    deadline = time.monotonic() + 3.0
    while sub.revision != 2 and time.monotonic() < deadline:
        client.poll()
    assert sub.revision == 2
    now[0] = 7.0
    sub.poll()
    assert router.poll(1000)
    retry_identity, retry = router.recv_multipart()
    assert retry_identity == identity
    assert deserialize(retry, None) == request

    # A response describing the earlier revision must not roll back live state.
    router.send_multipart(
        [identity, *response_frames((request[0], request[1], pub.epoch, 1, None))]
    )
    assert sub.socket.poll(1000)
    sub.poll()
    assert sub.pending is None
    assert sub.revision == 2
    np.testing.assert_equal(received[-1].a, source.a)


@pytest.mark.parametrize("tail", [0, 1])
def test_suffixes_atomic_delivery_and_ownership(transport, tail, monkeypatch):
    server, client, conf = transport
    pub = publisher(server, conf, tail)
    delivered, wire = [], []
    sub = IncrementalSubscriber(client, conf, delivered.append)
    client.add_sub(conf["pub_endpoint"], TOPIC, wire.append)
    source = SimpleNamespace(a=np.arange(12).reshape(3, 4), b=None, params={"x": 1})
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 1 and bool(wire))
    # After bootstrap, revisions must arrive through live publications alone.
    monkeypatch.setattr(sub, "poll", lambda: None)
    original = delivered[-1]
    original_copy = copy.deepcopy(original)
    source.a[:, -1] += 100 if tail else 0
    source.a = np.concatenate((source.a, np.ones((3, 2), dtype=int)), axis=1)
    source.b = source.a.copy()
    source.params["x"] = 2
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 2 and len(wire) == 2)
    assert wire[-1][-1]["a"][3].shape == (3, 2 + tail)
    np.testing.assert_array_equal(delivered[-1].a, source.a)
    np.testing.assert_array_equal(delivered[-1].b, source.b)
    np.testing.assert_array_equal(original.a, original_copy.a)
    assert original.params == {"x": 1}
    # Consumers can mutate their copy without corrupting the next reconstructed revision.
    delivered[-1].a[:] = -1
    source.params["x"] = 3
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 3)
    np.testing.assert_array_equal(delivered[-1].a, source.a)
    # The snapshot must not include unpublished mutations of the worker object.
    source.a[:] = 999
    source.params["x"] = 99
    late = []
    other = IncrementalSubscriber(client, conf, late.append)
    pump(server, client, lambda: other.revision == 3)
    np.testing.assert_array_equal(late[-1].a, pub.state.a)
    assert late[-1].params == {"x": 3}


def test_lost_final_update_and_late_join(transport, recovery_clock):
    server, client, conf = transport
    pub = publisher(server, conf)
    delivered = []
    sub = IncrementalSubscriber(client, conf, delivered.append)
    source = SimpleNamespace(a=np.ones((2, 1)), b=None, running=True)
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 1)
    # Simulate a subscriber losing all PUB messages, including the final one.
    for socket in client.sub_handlers:
        socket.setsockopt(zmq.UNSUBSCRIBE, TOPIC)
    source.a = np.ones((2, 4))
    source.running = False
    pub.publish(source)
    recovery_clock[0] += 1.0
    pump(server, client, lambda: sub.revision == 2)
    assert delivered[-1].a.shape == (2, 4)
    assert not delivered[-1].running
    late = []
    other = IncrementalSubscriber(client, conf, late.append)
    pump(server, client, lambda: other.revision == 2)
    np.testing.assert_array_equal(late[-1].a, delivered[-1].a)


def test_gap_is_not_applied_and_recovers(transport):
    server, client, conf = transport
    pub = publisher(server, conf)
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    source = SimpleNamespace(a=np.ones((2, 1)), b=None)
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 1)
    # Drop exactly revision 2 at the receive boundary.
    socket = next(iter(client.sub_handlers))
    handler, msg_type, deserial = client.sub_handlers[socket]
    client.sub_handlers[socket] = (
        lambda frames: handler(frames) if deserialize(frames[1], None)[3] != 2 else None,
        msg_type,
        deserial,
    )
    source.a = np.ones((2, 2))
    pub.publish(source)
    source.a = np.full((2, 3), 1.0)
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 3)
    assert [m.a.shape[1] for m in received] == [1, 3]


@pytest.mark.parametrize("axis", [0, 1])
def test_replacements_clear_and_invalidation(transport, axis):
    server, client, conf = transport
    pub = publisher(server, conf, axis=axis)
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    source = SimpleNamespace(a=np.ones((3, 4)), b=None)
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 1)
    for value in (np.ones((2, 2)), np.ones((2, 2), dtype=complex), None, np.zeros((4, 3))):
        source.a = value
        pub.publish(source)
        pump(server, client, lambda: sub.revision == pub.revision)
        np.testing.assert_equal(received[-1].a, value)
    old_epoch = sub.epoch
    source.a[:] = -10
    pub.invalidate()
    pub.publish(source)
    pump(server, client, lambda: sub.epoch != old_epoch)
    np.testing.assert_equal(received[-1].a, source.a)
    old_epoch = sub.epoch
    source = SimpleNamespace(a=np.full((4, 3), 20), b=None)
    pub.publish(source)
    pump(server, client, lambda: sub.epoch != old_epoch)
    np.testing.assert_equal(received[-1].a, source.a)


def test_restart_and_unchanged_revision(transport, tmp_path, recovery_clock):
    server, client, conf = transport
    conf["pub_endpoint"] = f"ipc://{tmp_path}/pub"
    conf["sync_endpoint"] = f"ipc://{tmp_path}/sync"
    pub = publisher(server, conf)
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    pub.publish(SimpleNamespace(a=np.zeros((2, 2)), b=None))
    pump(server, client, lambda: sub.revision == 1)
    recovery_clock[0] += 1.0
    pump(server, client, lambda: sub.pending is not None)
    pump(server, client, lambda: sub.pending is None)
    assert len(received) == 1
    old_epoch = sub.epoch
    server.close()
    restarted = Context(server.zmq_context(), poll_timeout_ms=1)
    try:
        pub = publisher(restarted, conf)
        pub.publish(SimpleNamespace(a=np.ones((2, 2)), b=None))
        recovery_clock[0] += 1.0
        pump(restarted, client, lambda: sub.epoch != old_epoch)
        np.testing.assert_equal(received[-1].a, np.ones((2, 2)))
    finally:
        restarted.close()


def test_configuration_validation():
    assert TransportConfig({}).mode == "pubsub"
    for conf in ({"data_transport": "typo"}, {"data_transport": "incremental"}):
        with pytest.raises(ValueError):
            TransportConfig(conf)
    with pytest.raises(ValueError):
        ArrayPolicy(1, -1)


def test_mutable_tail_without_growth(transport, monkeypatch):
    server, client, conf = transport
    pub = publisher(server, conf, tail=1)
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    source = SimpleNamespace(a=np.full((4, 2), np.nan), b=np.full((4, 2), np.nan))
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 1)
    # After bootstrap, revisions must arrive through live publications alone.
    monkeypatch.setattr(sub, "poll", lambda: None)
    for i in range(4):
        source.a[i, -1] = i
        source.b[i, -1] = 10 + i
        pub.publish(source)
        pump(server, client, lambda: sub.revision == pub.revision)
        np.testing.assert_equal(received[-1].a, source.a)
        np.testing.assert_equal(received[-1].b, source.b)
    assert np.isnan(received[0].a).all()


@pytest.mark.parametrize("capacity", [0, 1, 4])
@pytest.mark.parametrize("axis", [0, 1])
def test_counted_rolling_arrays(transport, capacity, axis, recovery_clock):
    server, client, conf = transport
    pub = IncrementalPublisher(
        server,
        conf["pub_endpoint"],
        conf["sync_endpoint"],
        {"a": ArrayPolicy(axis, count_attr="count")},
    )
    received, wire = [], []
    sub = IncrementalSubscriber(client, conf, received.append)
    client.add_sub(conf["pub_endpoint"], TOPIC, wire.append)
    source = SimpleNamespace(a=None, count=0)
    # Include unchanged counts, overlapping windows, and complete window turnover.
    for count in (2, 3, 3, 5, 12):
        length = min(capacity, count) if capacity else count
        source.a = np.arange(count - length, count).reshape((-1, 1))
        if axis == 1:
            source.a = source.a.T
        source.count = count
        old_count = pub.state.count if pub.state is not None else 0
        pub.publish(source)
        pump(server, client, lambda: sub.revision == pub.revision and len(wire) == pub.revision)
        np.testing.assert_equal(received[-1].a, source.a)
        payload = wire[-1][-1]["a"][-1]
        assert payload.shape[axis] == min(count - old_count, length)
    first = received[0].a.copy()
    # Miss the final rolling update and recover the exact bounded window via a snapshot.
    for socket in client.sub_handlers:
        socket.setsockopt(zmq.UNSUBSCRIBE, TOPIC)
    source.count += 1
    source.a = source.a + 1
    pub.publish(source)
    recovery_clock[0] += 1.0
    pump(server, client, lambda: sub.revision == pub.revision)
    np.testing.assert_equal(received[-1].a, source.a)
    np.testing.assert_equal(received[0].a, first)
    late = []
    other = IncrementalSubscriber(client, conf, late.append)
    pump(server, client, lambda: other.revision == pub.revision)
    np.testing.assert_equal(late[-1].a, source.a)


def test_same_shape_history_rebuild(transport, monkeypatch):
    server, client, conf = transport
    pub = IncrementalPublisher(
        server,
        conf["pub_endpoint"],
        conf["sync_endpoint"],
        {"a": ArrayPolicy(0, generation_attr="generation")},
    )
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    source = SimpleNamespace(a=np.ones((4, 2)), generation=0)
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 1)
    # After bootstrap, revisions must arrive through live publications alone.
    monkeypatch.setattr(sub, "poll", lambda: None)
    source.a[:] = 20
    source.generation += 1
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 2)
    np.testing.assert_equal(received[-1].a, source.a)
    np.testing.assert_equal(received[0].a, np.ones((4, 2)))


@pytest.mark.parametrize(
    "frames",
    [
        [b"not a pickle"],
        [serialize(())],
        [serialize((999,))],  # Version is checked before the envelope shape.
        [serialize((transport_module.VERSION, "request", None, 0))],
        [serialize((transport_module.VERSION, "request", None, -1, True))],
        [b"", serialize((transport_module.VERSION, "request", None, 0, True))],
    ],
)
def test_invalid_requests_do_not_stop_server(transport, frames, caplog):
    server, client, conf = transport
    pub = publisher(server, conf)
    pub.publish(SimpleNamespace(a=np.ones((2, 1)), b=None))
    dealer = client.zmq_context().socket(zmq.DEALER)
    dealer.setsockopt(zmq.LINGER, 0)
    dealer.connect(conf["sync_endpoint"])
    try:
        dealer.send_multipart(frames)
        dealer.send(serialize((transport_module.VERSION, "valid", None, 0, True)))
        assert dealer.poll(1000)
        header, snapshot = dealer.recv_multipart()
        assert deserialize(header, None)[1] == "valid"
        np.testing.assert_equal(deserialize(snapshot, None).a, pub.state.a)
        server.poll()  # Worker records are forwarded by the owning node thread.
        assert "Rejected recovery request" in caplog.text
    finally:
        dealer.close()


@pytest.mark.parametrize("invalid", ["pickle", "frames", "version", "revision", "array"])
def test_invalid_publication_preserves_replica(transport, invalid, caplog):
    server, client, conf = transport
    pub = publisher(server, conf)
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    source = SimpleNamespace(a=np.ones((2, 1)), b=np.ones((2, 1)))
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 1)
    original = sub.state
    metadata = SimpleNamespace(a=None, b=None)
    operations = {"a": (1, 0, 1, np.zeros((2, 1))), "b": (1, 0, 20, np.zeros((2, 1)))}
    update = (transport_module.VERSION, pub.epoch, 1, 2, metadata, operations)
    frames = [TOPIC, serialize(update)]
    if invalid == "pickle":
        frames[1] = b"not a pickle"
    elif invalid == "frames":
        frames.append(b"extra")
    elif invalid == "version":
        frames[1] = serialize((999,))
    elif invalid == "revision":
        frames[1] = serialize((transport_module.VERSION, pub.epoch, 1, 4, metadata, operations))
    pub.publisher.socket().send_multipart(frames)
    pump(server, client, lambda: bool(caplog.records))
    assert sub.state is original
    assert sub.revision == 1
    assert len(received) == 1
    assert sub.needs_snapshot
    if invalid == "version":
        assert "Incompatible incremental protocol version" in caplog.text
    # A header-only response confirming the retained replica completes recovery.
    pump(server, client, lambda: not sub.needs_snapshot)
    assert sub.state is original
    assert len(received) == 1
    source.a = np.ones((2, 2))
    source.b = np.ones((2, 2))
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 2)
    np.testing.assert_equal(received[-1].a, source.a)
    np.testing.assert_equal(received[-1].b, source.b)


@pytest.mark.parametrize("invalid", ["pickle", "frames", "version", "snapshot"])
def test_invalid_response_does_not_complete_request(controlled_recovery, invalid, caplog):
    server, client, conf, pub, router = controlled_recovery
    pub.publish(SimpleNamespace(a=np.ones((2, 1)), b=None))
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    sub.poll()
    assert router.poll(1000)
    identity, payload = router.recv_multipart()
    request = deserialize(payload, None)
    response = (transport_module.VERSION, request[1], pub.epoch, 1, pub.state)
    frames = [identity, *response_frames(response)]
    if invalid == "pickle":
        frames[1] = b"not a pickle"
    elif invalid == "frames":
        frames.append(b"extra")
    elif invalid == "version":
        frames[1] = serialize((999,))
    else:
        frames[2] = serialize(123)
    router.send_multipart(frames)
    assert sub.socket.poll(1000)
    sub.poll()
    assert caplog.records
    assert sub.state is None
    assert sub.pending == request[1]
    assert not received
    router.send_multipart([identity, *response_frames(response)])
    assert sub.socket.poll(1000)
    sub.poll()
    assert sub.pending is None
    np.testing.assert_equal(received[-1].a, pub.state.a)


def test_application_handler_errors_are_not_transport_errors(transport, caplog):
    server, client, conf = transport
    pub = publisher(server, conf)
    sub = IncrementalSubscriber(client, conf, lambda data: None)
    pub.publish(SimpleNamespace(a=np.ones((2, 1)), b=None))
    pump(server, client, lambda: sub.revision == 1)

    def fail(data):
        raise RuntimeError("application failure")

    sub.handler = fail
    metadata = SimpleNamespace(a=None, b=None)
    update = (
        transport_module.VERSION,
        pub.epoch,
        1,
        2,
        metadata,
        {"a": (1, 0, 1, np.ones((2, 1))), "b": (1, 0, 0, None)},
    )
    with pytest.raises(RuntimeError, match="application failure"):
        sub.handle_frames([TOPIC, serialize(update)])
    assert not caplog.records
    assert sub.revision == 2


def recovery_dealer(context, endpoint):
    dealer = context.zmq_context().socket(zmq.DEALER)
    dealer.setsockopt(zmq.LINGER, 0)
    dealer.connect(endpoint)
    return dealer


def receive_snapshot(dealer):
    assert dealer.poll(3000)
    frames = dealer.recv_multipart()
    header = deserialize(frames[0], None)
    return header, deserialize(frames[1], None) if len(frames) == 2 else None


def test_snapshot_cache_is_lazy_and_shared(transport, monkeypatch):
    server, client, conf = transport
    serialized = []
    original_serialize = transport_module.serialize_pickle

    def record_serialization(msg, **kwargs):
        if isinstance(msg, SimpleNamespace):
            serialized.append((threading.get_ident(), msg))
        return original_serialize(msg, **kwargs)

    monkeypatch.setattr(transport_module, "serialize_pickle", record_serialization)
    pub = publisher(server, conf)
    dealers = [recovery_dealer(client, conf["sync_endpoint"]) for _ in range(2)]
    try:
        source = SimpleNamespace(a=np.ones((2, 1)), b=None, note="one")
        for note in ("one", "two", "three"):
            source.note = note
            pub.publish(source)
        assert not serialized
        # No node polling anywhere in this test: recovery runs independently.
        dealers[0].send(serialize((transport_module.VERSION, "head", None, 0, False)))
        header, state = receive_snapshot(dealers[0])
        assert header[3] == 3 and state is None
        assert not serialized
        for i, dealer in enumerate(dealers):
            dealer.send(serialize((transport_module.VERSION, str(i), None, 0, True)))
            header, state = receive_snapshot(dealer)
            assert header[1] == str(i) and header[3] == 3
            assert state.note == "three"
        assert len(serialized) == 1
        assert serialized[0][0] != threading.get_ident()
        source.note = "four"
        pub.publish(source)
        assert len(serialized) == 1
        source.note = "unpublished"
        dealers[0].send(serialize((transport_module.VERSION, "next", None, 0, True)))
        header, state = receive_snapshot(dealers[0])
        assert header[3] == 4 and state.note == "four"
        assert len(serialized) == 2
        # Epoch changes must invalidate the cache even if revision numbers repeat.
        pub.publish(SimpleNamespace(a=np.zeros((2, 1)), b=None, note="new epoch"))
        dealers[0].send(serialize((transport_module.VERSION, "reset", None, 0, True)))
        header, state = receive_snapshot(dealers[0])
        assert header[2:4] == (pub.epoch, 1)
        assert state.note == "new epoch"
        assert len(serialized) == 3
    finally:
        for dealer in dealers:
            dealer.close()
        server.close()
    assert not pub.snapshot_service._thread.is_alive()
    assert pub.snapshot_service._cache_payload is None
    assert pub.snapshot_service._latest is None
    server.close()  # Idempotent shutdown.


def test_publication_during_snapshot_and_queued_retry_coalescing(transport, monkeypatch):
    server, client, conf = transport
    entered, release = threading.Event(), threading.Event()
    serialized = []
    original_serialize = transport_module.serialize_pickle

    def slow_serialization(msg, **kwargs):
        if isinstance(msg, SimpleNamespace):
            serialized.append(msg)
            if len(serialized) == 1:
                entered.set()
                assert release.wait(5)
        return original_serialize(msg, **kwargs)

    monkeypatch.setattr(transport_module, "serialize_pickle", slow_serialization)
    pub = publisher(server, conf)
    first = recovery_dealer(client, conf["sync_endpoint"])
    second = recovery_dealer(client, conf["sync_endpoint"])
    try:
        source = SimpleNamespace(a=np.ones((2, 1)), b=None)
        pub.publish(source)
        first.send(serialize((transport_module.VERSION, "first", None, 0, True)))
        assert entered.wait(3)
        # Commit on the node thread while the service is blocked serializing revision 1.
        source.a = np.concatenate((source.a, np.full((2, 1), 2)), axis=1)
        pub.publish(source)
        request = serialize((transport_module.VERSION, "retry", None, 0, True))
        for _ in range(10):
            second.send(request)
        release.set()
        header, state = receive_snapshot(first)
        assert header[3] == 1
        np.testing.assert_equal(state.a, np.ones((2, 1)))
        header, state = receive_snapshot(second)
        assert header[3] == 2
        np.testing.assert_equal(state.a, source.a)
        assert not second.poll(100)  # Ten queued retries produced one response.
        assert len(serialized) == 2
        # A later retry must still get a response if the first response was lost.
        second.send(request)
        header, state = receive_snapshot(second)
        assert header[3] == 2
        assert len(serialized) == 2
    finally:
        release.set()
        first.close()
        second.close()
        server.close()


def test_snapshot_service_bind_failure_does_not_leak_thread(transport):
    server, client, conf = transport
    pub = publisher(server, conf)
    # Qt may finish unrelated dummy threads while this test runs.
    before = {t for t in threading.enumerate() if t.name == "mahos-snapshot"}
    with pytest.raises(zmq.ZMQError):
        transport_module.SnapshotService(
            server.zmq_context(), conf["sync_endpoint"], ("epoch", 0, None), DummyLogger()
        )
    assert {t for t in threading.enumerate() if t.name == "mahos-snapshot"} == before
    dealer = recovery_dealer(client, conf["sync_endpoint"])
    try:
        dealer.send(serialize((transport_module.VERSION, "still-alive", None, 0, True)))
        header, state = receive_snapshot(dealer)
        assert header[2] == pub.epoch and state is None
    finally:
        dealer.close()


def test_shutdown_joins_in_progress_snapshot(transport, monkeypatch):
    server, client, conf = transport
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()
    original_serialize = transport_module.serialize_pickle

    def slow_serialization(msg, **kwargs):
        if isinstance(msg, SimpleNamespace):
            entered.set()
            assert release.wait(5)
        return original_serialize(msg, **kwargs)

    monkeypatch.setattr(transport_module, "serialize_pickle", slow_serialization)
    pub = publisher(server, conf)
    dealer = recovery_dealer(client, conf["sync_endpoint"])
    closer = None
    try:
        pub.publish(SimpleNamespace(a=np.ones((2, 1)), b=None))
        dealer.send(serialize((transport_module.VERSION, "snapshot", None, 0, True)))
        assert entered.wait(3)

        def close_service():
            pub.snapshot_service.close()
            closed.set()

        closer = threading.Thread(target=close_service)
        closer.start()
        assert pub.snapshot_service._stop.wait(3)
        assert not closed.is_set()
        release.set()
        assert closed.wait(3)
        assert not pub.snapshot_service._thread.is_alive()
    finally:
        release.set()
        if closer is not None:
            closer.join()
        dealer.close()
        server.close()


def test_snapshots_bypass_custom_message_serialization(transport, recovery_clock):
    server, client, conf = transport
    pub = publisher(server, conf)
    received = []
    sub = IncrementalSubscriber(client, conf, received.append)
    source = CompressedData()
    assert isinstance(CompressedData.deserialize(source.serialize()), CompressedData)
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 1)
    assert type(received[-1]) is CompressedData
    np.testing.assert_equal(received[-1].a, source.a)
    source.a = np.ones((2, 2))
    pub.publish(source)
    pump(server, client, lambda: sub.revision == 2)
    # Recovery and late joins also use the fixed snapshot encoding.
    for socket in client.sub_handlers:
        socket.setsockopt(zmq.UNSUBSCRIBE, TOPIC)
    source.a = np.ones((2, 3))
    pub.publish(source)
    recovery_clock[0] += 1.0
    pump(server, client, lambda: sub.revision == 3)
    late = []
    other = IncrementalSubscriber(client, conf, late.append)
    pump(server, client, lambda: other.revision == 3)
    for result in (received[-1], late[-1]):
        assert type(result) is CompressedData
        np.testing.assert_equal(result.a, source.a)
