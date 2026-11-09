"""Shared fixtures and polling helpers for transport tests."""

import time
import uuid

import pytest
import zmq

from mahos.node.comm import Context


@pytest.fixture
def transport_contexts():
    """Provide server and client contexts sharing one ZeroMQ context."""

    zctx = zmq.Context()
    server = Context(zctx, poll_timeout_ms=1)
    client = Context(zctx, poll_timeout_ms=1)
    yield server, client
    client.close()
    server.close()
    zctx.term()


@pytest.fixture
def transport(transport_contexts):
    server, client = transport_contexts
    suffix = uuid.uuid4().hex
    conf = {
        "data_transport": "incremental",
        "pub_endpoint": f"inproc://pub-{suffix}",
        "sync_endpoint": f"inproc://sync-{suffix}",
    }
    yield server, client, conf


def pump(server, client, condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        server.poll()
        client.poll()
    assert condition()
