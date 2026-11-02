#!/usr/bin/env python3

import pytest
import zmq

from mahos.node.comm import Context

from shared.fixtures import (
    ctx,
    gconf,
    global_params,
    global_params_2clients,
    gparams_conf,
    log_broker,
    dummy_logging,
    server_restart,
    server_conf,
)


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
