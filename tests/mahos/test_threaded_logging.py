"""
Threaded transport logging and handler lifecycle tests.

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
from mahos.node.log import PUBHandler
from mahos.node.node import Node


class RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []
        self.emit_threads = []

    def emit(self, record):
        self.records.append(copy.copy(record))
        self.emit_threads.append(threading.get_ident())


def test_node_shutdown_joins_snapshot_worker_before_detaching_handler(monkeypatch):
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
        pub = IncrementalPublisher(
            node.ctx, f"inproc://pub-{suffix}", sync, {"data": ArrayPolicy(0)}, logger=node.logger
        )
        log_handler = node._log_handler
        remove_handler = node.logger.removeHandler
        worker_alive_at_detach = []

        def observe_handler_removal(handler):
            if handler is log_handler:
                worker_alive_at_detach.append(pub.snapshot_service._thread.is_alive())
            remove_handler(handler)

        monkeypatch.setattr(node.logger, "removeHandler", observe_handler_removal)
        dealer.send(b"invalid pickle")
        dealer.send(serialize((VERSION, "barrier", None, 0, False)))
        assert dealer.poll(3000)
        assert deserialize(dealer.recv_multipart()[0], None)[1] == "barrier"
        assert len(handler.records) == 1
        node.close()
        assert worker_alive_at_detach == [False]
        assert not pub.snapshot_service._thread.is_alive()
        assert len(handler.records) == 1
        assert "Rejected recovery request" in handler.records[0].msg
        assert handler.emit_threads == [pub.snapshot_service._thread.ident]
        assert pub_threads == handler.emit_threads
        assert node._log_handler is None
        assert log_handler not in node.logger.handlers
    finally:
        node.close()
        node.logger.removeHandler(handler)
        dealer.close()
        logs.close()
        zctx.term()


def test_python_client_logs_without_getter_or_parent_poll():
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
    destination = logging.getLogger(f"logging-test-{suffix}")
    destination.setLevel(logging.INFO)
    handler = RecordingHandler()
    destination.addHandler(handler)
    cli = None
    try:
        pub = IncrementalPublisher(
            server, conf["pub_endpoint"], conf["sync_endpoint"], {"data": ArrayPolicy(0)}
        )
        cli = StatusDataSubscriber(
            {"localhost": {"node": conf}},
            "localhost::node",
            context=server,
            prefix=destination.name,
        )
        deadline = time.monotonic() + 3
        while not handler.records and time.monotonic() < deadline:
            pub.publisher.socket().send_multipart([TOPIC, b"bad pickle"])
            time.sleep(0.01)
        assert handler.records
        cli.close()
        assert cli.get_data() is None
        assert all(t == cli._subscribers[0][1].ident for t in handler.emit_threads)
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


@pytest.mark.parametrize("logger_kind", ["none", "pub"])
def test_qt_client_logs_without_gui_event_loop(qapp, capsys, logger_kind):
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
    if logger_kind == "pub":
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
            {"localhost": {"node": conf}},
            "localhost::node",
            context=zctx,
            prefix=destination.name if destination is not None else None,
        )
        assert cli.req.logger is cli.logger
        deadline = time.monotonic() + 3
        # Diagnostics must arrive while the Qt main loop is paused.
        output = ""
        while not handler.records and not output and time.monotonic() < deadline:
            pub.publisher.socket().send_multipart([TOPIC, b"bad pickle"])
            time.sleep(0.01)
            output += capsys.readouterr().out
        cli.close()
        if logger_kind == "pub":
            assert output == ""
            assert handler.records
            assert all(t != threading.get_ident() for t in handler.emit_threads)
            assert pub_threads == handler.emit_threads
            assert all(r.thread == t for r, t in zip(handler.records, handler.emit_threads))
            assert handler.records[0].msg.startswith(
                "QBasicMeasClient(localhost::node)->Rejected incremental message"
            )
            assert cli.logger.parent is destination
            assert not cli.logger.handlers
        else:
            assert "QBasicMeasClient(localhost::node)" in output
            assert "Rejected incremental message" in output
    finally:
        if cli is not None:
            cli.close()
        if logger_kind == "pub":
            destination.removeHandler(handler)
            destination.removeHandler(pub_handler)
        server.close()
        zctx.term()


def test_pub_handler_serializes_threaded_multipart_logs():
    context = zmq.Context()
    endpoint = f"inproc://threaded-logs-{uuid.uuid4().hex}"
    socket = context.socket(zmq.PUB)
    socket.bind(endpoint)
    subscriber = context.socket(zmq.SUB)
    subscriber.subscribe(b"")
    subscriber.connect(endpoint)
    handler = PUBHandler(socket, root_topic="node")
    logger = logging.Logger("threaded-pub", logging.INFO)
    logger.addHandler(handler)
    workers = []
    try:
        # Establish the subscription before checking delivery of every multipart record.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            logger.info("ready")
            if subscriber.poll(10):
                assert subscriber.recv_multipart()[0] == b"node->INFO"
                break
        else:
            pytest.fail("Log subscription did not become ready")

        barrier = threading.Barrier(5)

        def produce(index):
            barrier.wait(timeout=3)
            for message in range(50):
                logger.info(f"worker{index}->message %d", message)

        workers = [threading.Thread(target=produce, args=(i,)) for i in range(4)]
        for worker in workers:
            worker.start()
        produce(4)
        for worker in workers:
            worker.join(timeout=3)
            assert not worker.is_alive()
        handler.close()
        handler.close()
        logger.info("ignored after close")

        received = set()
        for _ in range(250):
            assert subscriber.poll(3000)
            topic, body = subscriber.recv_multipart()
            received.add((topic, body.decode().split(";", 1)[1]))
        assert received == {
            (f"node->INFO->worker{i}".encode(), f"message {j}\n")
            for i in range(5)
            for j in range(50)
        }
        assert not subscriber.poll(10)
    finally:
        for worker in workers:
            worker.join(timeout=3)
        handler.close()
        subscriber.close(linger=0)
        context.term()
