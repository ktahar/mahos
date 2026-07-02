#!/usr/bin/env python3

"""
Tests for Spectrum digitizer internals.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np

from mahos.inst.digitizer import SpectrumAnalogIn
from mahos.util.queue import RollingQueue


class DummyTransfer:
    def __init__(self, bytes_per_sample=2, channels=1):
        self.bytes_per_sample = bytes_per_sample
        self.channels = channels

    def samples_to_bytes(self, samples):
        return int(samples) * self.bytes_per_sample * self.channels


def make_inst(conf=None):
    return SpectrumAnalogIn("digitizer", {"mock": True, "lines": [0], **(conf or {})})


def test_align_notify_samples_uses_transfer_byte_size():
    inst = make_inst()
    inst._transfer = DummyTransfer(bytes_per_sample=2, channels=1)

    assert inst._align_notify_samples(5) == 2048

    inst._transfer = DummyTransfer(bytes_per_sample=2, channels=2)

    assert inst._align_notify_samples(5) == 1024


def test_align_notify_samples_preserves_segment_boundary():
    inst = make_inst()
    inst._transfer = DummyTransfer(bytes_per_sample=2, channels=1)

    samples = inst._align_notify_samples(1500, step_samples=512)

    assert samples >= 1500
    assert samples % 512 == 0
    assert inst._samples_to_bytes(samples) % 4096 == 0


def test_align_buffer_samples_is_notify_multiple():
    inst = make_inst()

    assert inst._align_buffer_samples(5000, 2048) == 6144


def test_append_stream_samples_reblocks_aligned_notifications():
    inst = make_inst()
    inst.queue = RollingQueue(100)
    inst._line_num = 1
    inst._stamp = False
    inst._oversample = 2
    inst._stream_samples = 4
    inst._pending = [[]]

    inst._append_stream_samples([np.arange(10.0)])

    np.testing.assert_allclose(inst.pop_opt(), np.array([0.5, 2.5]))
    np.testing.assert_allclose(inst.pop_opt(), np.array([4.5, 6.5]))
    assert inst.pop_opt() is None
    np.testing.assert_allclose(inst._pending[0][0], np.array([8.0, 9.0]))


def test_append_stream_samples_handles_multi_channel_blocks():
    inst = make_inst({"lines": [0, 1]})
    inst.queue = RollingQueue(100)
    inst._line_num = 2
    inst._stamp = False
    inst._oversample = 1
    inst._stream_samples = 3
    inst._pending = [[], []]

    inst._append_stream_samples([np.array([1.0, 2.0]), np.array([10.0, 20.0])])
    assert inst.pop_opt() is None

    inst._append_stream_samples([np.array([3.0, 4.0]), np.array([30.0, 40.0])])
    data = inst.pop_opt()

    np.testing.assert_allclose(data[0], np.array([1.0, 2.0, 3.0]))
    np.testing.assert_allclose(data[1], np.array([10.0, 20.0, 30.0]))
    np.testing.assert_allclose(inst._pending[0][0], np.array([4.0]))
    np.testing.assert_allclose(inst._pending[1][0], np.array([40.0]))


def test_configure_triggered_rejects_nondivisible_software_block_reduce(monkeypatch):
    inst = make_inst()
    errors = []
    params = {
        "trigger_source": "software",
        "cb_samples": 24,
        "samples": 24,
        "rate": 1.0e6,
        "segment_samples": 48,
        "block_reduce_factor": 2,
        "block_reduce_samples": 10,
        "hardware_average": False,
    }

    monkeypatch.setattr(inst, "_import_spcm", lambda: object())
    monkeypatch.setattr(inst, "_open_card", lambda: object())
    monkeypatch.setattr(inst, "fail_with", lambda msg: errors.append(msg) or False)

    assert not inst.configure_triggered(params)
    assert errors == ["cb_samples must be integer multiple of block_reduce_samples."]
