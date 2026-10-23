"""
Thread ownership and lifecycle tests for queued transport logging.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import copy
import logging
import threading
import time
import uuid

import pytest
import zmq

from mahos.node.comm import serialize, deserialize
from mahos.node.data_transport import IncrementalPublisher, ArrayPolicy, VERSION
from mahos.node.log import QueuedLogger, TopicLogger, DummyLogger
from mahos.node.node import Node


class RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []
        self.emit_threads = []

    def emit(self, record):
        self.records.append(copy.copy(record))
        self.emit_threads.append(threading.get_ident())


def test_queue_preserves_origin_exception_and_topic():
    destination = TopicLogger("node.client")
    destination.set_topic("client")
    destination.setLevel(logging.INFO)
    handler = RecordingHandler()
    destination.addHandler(handler)
    queue = QueuedLogger(destination)

    def produce():
        queue.debug("filtered")
        queue.warning("revision %d", 42)
        try:
            raise ValueError("bad response")
        except ValueError:
            queue.exception("decoding failed")
        queue.poll()  # Must never invoke handlers from this thread.

    worker = threading.Thread(target=produce)
    worker.start()
    worker.join()
    assert not handler.records
    queue.poll()
    assert handler.emit_threads == [threading.get_ident()] * 2
    warning, error = handler.records
    assert warning.msg == "client->revision 42"
    assert warning.thread == worker.ident
    assert warning.pathname == __file__
    assert warning.name == destination.name
    assert error.msg.startswith("client->decoding failed")
    assert "ValueError: bad response" in error.msg
    assert error.exc_info is None  # No retained worker traceback frames.
    queue.close()
    assert len(handler.records) == 2


def test_queue_overflow_is_bounded_and_reported():
    destination = logging.Logger("bounded", logging.DEBUG)
    handler = RecordingHandler()
    destination.addHandler(handler)
    queue = QueuedLogger(destination)
    for i in range(1030):
        queue.warning("message %d", i)
    queue.close()
    assert len(handler.records) == 1025
    assert handler.records[-1].msg == "Dropped 6 queued log records"
    queue.poll()
    assert len(handler.records) == 1025


def test_queue_formats_dummy_logger_messages(capsys):
    queue = QueuedLogger(DummyLogger("client"))
    queue.warning("revision %d", 3)
    assert capsys.readouterr().out == ""
    queue.poll()
    assert "revision 3" in capsys.readouterr().out


def test_node_shutdown_flushes_snapshot_logs_before_detaching_handler():
    zctx = zmq.Context()
    suffix = uuid.uuid4().hex
    endpoint = f"inproc://log-{suffix}"
    logs = zctx.socket(zmq.SUB)
    logs.setsockopt(zmq.SUBSCRIBE, b"")
    logs.bind(endpoint)
    gconf = {
        "localhost": {
            "node": {"target": {"log": "localhost::log"}},
            "log": {"xsub_endpoint": endpoint},
        }
    }
    node = Node(gconf, "localhost::node", context=zctx)
    handler = RecordingHandler()
    node.logger.addHandler(handler)
    pub_threads = []
    node._log_handler.addFilter(lambda record: pub_threads.append(threading.get_ident()) or True)
    sync = f"inproc://sync-{suffix}"
    dealer = zctx.socket(zmq.DEALER)
    dealer.setsockopt(zmq.LINGER, 0)
    dealer.connect(sync)
    try:
        IncrementalPublisher(
            node.ctx, f"inproc://pub-{suffix}", sync, {"data": ArrayPolicy(0)}, logger=node.logger
        )
        dealer.send(b"invalid pickle")
        dealer.send(serialize((VERSION, "barrier", None, 0, False)))
        assert dealer.poll(3000)
        assert deserialize(dealer.recv_multipart()[0], None)[1] == "barrier"
        assert not handler.records
        node.close()
        assert len(handler.records) == 1
        assert "Rejected incremental recovery request" in handler.records[0].msg
        assert handler.emit_threads == [threading.get_ident()]
        assert pub_threads == [threading.get_ident()]
        assert node._log_handler is None
    finally:
        node.close()
        node.logger.removeHandler(handler)
        dealer.close()
        logs.close()
        zctx.term()


def test_python_client_getter_forwards_subscription_logs():
    from mahos.node.client import StatusDataSubscriber
    from mahos.node.comm import Context
    from mahos.node.data_transport import TOPIC

    zctx = zmq.Context()
    server = Context(zctx)
    suffix = uuid.uuid4().hex
    conf = {
        "pub_endpoint": f"inproc://pub-{suffix}",
        "sync_endpoint": f"inproc://sync-{suffix}",
        "data_transport": "incremental",
    }
    destination = logging.getLogger(f"queue-test-{suffix}")
    destination.setLevel(logging.INFO)
    handler = RecordingHandler()
    destination.addHandler(handler)
    cli = None
    try:
        pub = IncrementalPublisher(
            server, conf["pub_endpoint"], conf["sync_endpoint"], {"data": ArrayPolicy(0)}
        )
        cli = StatusDataSubscriber(
            {"localhost": {"node": conf}}, "localhost::node", context=zctx, prefix=destination.name
        )
        deadline = time.monotonic() + 3
        while not cli.ctx.log_queue._records and time.monotonic() < deadline:
            pub.publisher.socket().send_multipart([TOPIC, b"bad pickle"])
            time.sleep(0.01)
        assert cli.ctx.log_queue._records
        assert not handler.records
        assert cli.get_data() is None
        assert handler.records
        assert all(t == threading.get_ident() for t in handler.emit_threads)
        assert all(r.thread != threading.get_ident() for r in handler.records)
        assert (
            "StatusDataSubscriber(localhost::node)->Rejected incremental" in handler.records[0].msg
        )
    finally:
        if cli is not None:
            cli.close()
        server.close()
        destination.removeHandler(handler)
        zctx.term()


@pytest.mark.parametrize("logger_kind", ["none", "dummy", "pub"])
def test_qt_client_timer_forwards_subscription_logs(qtbot, capsys, logger_kind):
    from mahos.gui.client import QBasicMeasClient
    from mahos.node.comm import Context
    from mahos.node.data_transport import TOPIC

    zctx = zmq.Context()
    server = Context(zctx)
    suffix = uuid.uuid4().hex
    conf = {
        "pub_endpoint": f"inproc://pub-{suffix}",
        "sync_endpoint": f"inproc://sync-{suffix}",
        "rep_endpoint": f"inproc://rep-{suffix}",
        "data_transport": "incremental",
    }
    destination = None
    handler = RecordingHandler()
    pub_threads = []
    pub_handler = None
    if logger_kind == "dummy":
        destination = DummyLogger("gui")
    elif logger_kind == "pub":
        destination = logging.getLogger(f"gui-{suffix}")
        destination.setLevel(logging.INFO)
        destination.addHandler(handler)
        pub_handler = server.add_pub_handler(
            f"inproc://logs-{suffix}", root_topic=destination.name
        )
        pub_handler.addFilter(lambda record: pub_threads.append(threading.get_ident()) or True)
        destination.addHandler(pub_handler)
    cli = None
    try:
        pub = IncrementalPublisher(
            server, conf["pub_endpoint"], conf["sync_endpoint"], {"data": ArrayPolicy(0)}
        )
        cli = QBasicMeasClient(
            {"localhost": {"node": conf}}, "localhost::node", context=zctx, logger=destination
        )
        assert cli.req.logger is cli.logger
        deadline = time.monotonic() + 3
        # Keep the Qt main loop paused until a worker has queued the diagnostic.
        while not cli.ctx.log_queue._records and time.monotonic() < deadline:
            pub.publisher.socket().send_multipart([TOPIC, b"bad pickle"])
            time.sleep(0.01)
        assert cli.ctx.log_queue._records
        assert capsys.readouterr().out == ""
        assert not handler.records
        assert not pub_threads
        qtbot.waitUntil(lambda: not cli.ctx.log_queue._records, timeout=3000)
        output = capsys.readouterr().out
        if logger_kind == "pub":
            assert output == ""
            assert handler.records
            assert all(t == threading.get_ident() for t in handler.emit_threads)
            assert pub_threads == handler.emit_threads
            assert all(r.thread != threading.get_ident() for r in handler.records)
            assert handler.records[0].msg.startswith(
                "QBasicMeasClient(localhost::node)->Rejected incremental message"
            )
            assert cli.logger.parent is destination
            assert not cli.logger.handlers
            assert cli._log_timer.isActive()
        else:
            assert "QBasicMeasClient(localhost::node)" in output
            assert "Rejected incremental message" in output

        # Leave one worker record pending: close must drain it before handlers close.
        worker = threading.Thread(target=lambda: cli.ctx.log_queue.warning("final diagnostic"))
        worker.start()
        worker.join()
        cli.close()
        assert not cli._log_timer.isActive()
        assert cli.ctx.log_queue.closed
        if logger_kind == "pub":
            assert handler.records[-1].msg.endswith("final diagnostic")
            assert handler.records[-1].thread == worker.ident
            assert handler.emit_threads[-1] == threading.get_ident()
            assert pub_threads == handler.emit_threads
        else:
            assert "final diagnostic" in capsys.readouterr().out
    finally:
        if cli is not None:
            cli.close()
        if logger_kind == "pub":
            destination.removeHandler(handler)
            destination.removeHandler(pub_handler)
        server.close()
        zctx.term()


def test_parent_unregisters_closed_client_queues():
    from mahos.node.client import NodeClient
    from mahos.node.comm import Context

    zctx = zmq.Context()
    parent = Context(zctx, poll_timeout_ms=0)
    conf = {"localhost": {"node": {"data_transport": "incremental"}}}
    try:
        for _ in range(10):
            client = NodeClient(conf, "localhost::node", context=parent)
            queue = client.ctx.log_queue
            assert parent._child_log_queues == [queue]
            client.close()
            assert queue.closed
            # The client marks closure; the parent owns removal at its next poll.
            assert parent._child_log_queues == [queue]
            parent.poll()
            assert not parent._child_log_queues
    finally:
        parent.close()
        zctx.term()


def test_parent_drains_before_unregistering_foreign_thread_close():
    from mahos.node.comm import Context

    context = Context(poll_timeout_ms=0)
    destination = logging.Logger("parent-drain", logging.INFO)
    handler = RecordingHandler()
    destination.addHandler(handler)
    queue = QueuedLogger(destination)
    context.add_child_log_queue(queue)

    def finish():
        queue.warning("last worker message")
        queue.close()
        queue.warning("ignored after close")

    try:
        worker = threading.Thread(target=finish)
        worker.start()
        worker.join()
        assert not queue.closed
        assert not handler.records
        context.poll()
        assert queue.closed
        assert not context._child_log_queues
        assert [r.msg for r in handler.records] == ["last worker message"]
        assert handler.emit_threads == [threading.get_ident()]
    finally:
        context.close(close_zmq_ctx=True)


def test_close_during_drain_keeps_records_queued_before_closure():
    destination = logging.Logger("closing-race", logging.INFO)
    handler = RecordingHandler()
    destination.addHandler(handler)
    queue = QueuedLogger(destination)

    def finish():
        queue.warning("last")
        queue.close()

    def close_while_forwarding(record):
        if record.msg == "first":
            worker = threading.Thread(target=finish)
            worker.start()
            worker.join()
        return True

    handler.addFilter(close_while_forwarding)
    queue.warning("first")
    queue.poll()
    assert not queue.closed
    queue.poll()
    assert queue.closed
    assert [r.msg for r in handler.records] == ["first", "last"]


def test_parent_shutdown_releases_but_does_not_close_live_child_queue():
    from mahos.node.comm import Context

    context = Context(poll_timeout_ms=0)
    destination = logging.Logger("borrowed-queue", logging.INFO)
    handler = RecordingHandler()
    destination.addHandler(handler)
    queue = QueuedLogger(destination)
    context.add_child_log_queue(queue)
    context.close(close_zmq_ctx=True)
    assert not context._child_log_queues
    assert not queue.closed
    queue.warning("client still alive")
    queue.close()
    assert [r.msg for r in handler.records] == ["client still alive"]


def test_snapshot_service_shutdown_does_not_close_context_log_queue():
    from mahos.node.comm import Context

    context = Context(poll_timeout_ms=0)
    destination = logging.Logger("context-owned-queue", logging.INFO)
    handler = RecordingHandler()
    destination.addHandler(handler)
    suffix = uuid.uuid4().hex
    try:
        pub = IncrementalPublisher(
            context,
            f"inproc://pub-{suffix}",
            f"inproc://sync-{suffix}",
            {"data": ArrayPolicy(0)},
            logger=destination,
        )
        pub.snapshot_service.close()
        assert not context.log_queue.closed
        context.log_queue.warning("context still alive")
        context.poll()
        assert [r.msg for r in handler.records] == ["context still alive"]
    finally:
        context.close(close_zmq_ctx=True)
    assert context.log_queue.closed
