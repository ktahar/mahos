#!/usr/bin/env python3

import pytest

from shared.fixtures import (
    ctx,
    gconf,
    server,
    server_conf,
    odmr,
    odmr_conf,
    iodmr,
    iodmr_conf,
)


@pytest.fixture
def sg_power_bounds(server_conf):
    """Return the configured signal generator power bounds for ODMR tests."""

    return tuple(server_conf["instrument"]["sg"]["conf"]["power_bounds"])
