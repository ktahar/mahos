"""
Qt client threaded logging tests.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import logging
import threading
import time
import uuid

import pytest
import zmq

from mahos.node.transport.incremental import IncrementalPublisher, ArrayPolicy

from shared.logging import RecordingHandler
from mahos.node.transport import SnapshotService


@pytest.mark.parametrize("logger_kind", ["none", "pub"])
def test_qt_client_logs_without_gui_event_loop(qapp, capsys, logger_kind):
    from mahos.gui.client import QBasicMeasClient
    from mahos.node.comm import Context
    from mahos.node.transport.incremental import TOPIC

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
            server,
            conf["pub_endpoint"],
            {"data": ArrayPolicy(0)},
            SnapshotService(server, conf["sync_endpoint"], logging.getLogger(__name__)),
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
