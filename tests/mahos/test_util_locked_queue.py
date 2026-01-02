#!/usr/bin/env python3

"""
Tests for mahos.util.locked_queue.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.util.locked_queue import LockedQueue


def test_append_and_overflow():
    q = LockedQueue(2)
    assert q.append("a")
    assert q.append("b")
    assert not q.append("c")

    assert len(q) == 2
    assert q.pop_opt() == "b"
    assert q.pop_opt() == "c"


def test_pop_opt_empty():
    q = LockedQueue(1)
    assert q.pop_opt() is None


def test_pop_all_opt():
    q = LockedQueue(3)
    q.append(1)
    q.append(2)
    assert q.pop_all_opt() == [1, 2]
    assert len(q) == 0
    assert q.pop_all_opt() is None


def test_pop_block_timeout():
    q = LockedQueue(1)
    assert q.pop_block(timeout_sec=0.01, interval_sec=0.001) is None


def test_pop_all_block_with_data():
    q = LockedQueue(2)
    q.append("x")
    q.append("y")
    assert q.pop_all_block(timeout_sec=0.01, interval_sec=0.001) == ["x", "y"]
    assert len(q) == 0
