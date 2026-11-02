#!/usr/bin/env python3

import socket

import pytest

from shared.fixtures import (
    ctx,
    gconf,
    server,
    global_params,
    camera,
    sweeper,
    grid_sweeper,
    recorder,
    spectroscopy,
    odmr,
    hbt,
    podmr,
    apodmr,
    spodmr,
    iodmr,
)


@pytest.fixture
def sync_endpoint():
    """Return an available local TCP endpoint for measurement synchronization."""

    with socket.socket() as sync_socket:
        sync_socket.bind(("127.0.0.1", 0))
        return f"tcp://127.0.0.1:{sync_socket.getsockname()[1]}"
