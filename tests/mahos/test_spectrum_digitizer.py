#!/usr/bin/env python3

"""
Tests for Spectrum digitizer internals.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from mahos.inst.digitizer import SpectrumAnalogIn
from mahos.util.queue import RollingQueue


class DummyTransfer:
    def __init__(self, bytes_per_sample=2, channels=1):
        self.bytes_per_sample = bytes_per_sample
        self.channels = channels

    def samples_to_bytes(self, samples):
        return int(samples) * self.bytes_per_sample * self.channels


class ConfigureTransfer(DummyTransfer):
    def __init__(self, card):
        super().__init__()
        self.card = card

    def averages(self, averages):
        return averages

    def allocate_buffer(self, segment_samples, num_segments):
        self.buffer = np.zeros((num_segments, segment_samples, 1))

    def notify_samples(self, samples):
        self.notified = samples

    def to_transfer_samples(self, samples):
        self.transfer_samples = samples

    def post_trigger(self, samples):
        self.post_trigger_samples = samples


class DummyCard:
    def card_mode(self, mode):
        self.mode = mode

    def timeout(self, timeout):
        self.timeout_value = timeout

    def loops(self, loops):
        self.loop_count = loops


class DummyUnits:
    s = 1.0


class DummySpcm:
    SPC_REC_FIFO_AVERAGE = 1
    SPC_REC_FIFO_MULTI = 2
    units = DummyUnits()

    Multi = ConfigureTransfer
    BlockAverage = ConfigureTransfer


def make_inst(conf=None):
    return SpectrumAnalogIn("digitizer", {"mock": True, "lines": [0], **(conf or {})})


def configure_triggered(inst, monkeypatch, **overrides):
    card = DummyCard()
    params = {
        "trigger_source": "software",
        "cb_samples": 64,
        "samples": 192,
        "rate": 1.0e6,
        "finite": True,
        "block_samples": 32,
        **overrides,
    }
    monkeypatch.setattr(inst, "_import_spcm", lambda: DummySpcm)
    monkeypatch.setattr(inst, "_reset_card", lambda: card)
    monkeypatch.setattr(inst, "_setup_trigger", lambda _params: True)

    def setup_channels(_params):
        inst._channels = [object()]
        inst._line_num = 1
        return True

    monkeypatch.setattr(inst, "_setup_channels", setup_channels)
    monkeypatch.setattr(inst, "_setup_clock", lambda _params: True)
    assert inst.configure_triggered(params)
    return card, inst._transfer


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
        "block_samples": 32,
        "block_reduce_factor": 2,
        "hardware_average": False,
    }

    monkeypatch.setattr(inst, "_import_spcm", lambda: object())
    monkeypatch.setattr(inst, "_reset_card", lambda: object())
    monkeypatch.setattr(inst, "fail_with", lambda msg: errors.append(msg) or False)

    assert not inst.configure_triggered(params)
    assert errors == ["cb_samples must be integer multiple of block_samples."]


@pytest.mark.parametrize("samples", [0, -64, 65])
def test_configure_triggered_rejects_invalid_finite_samples(monkeypatch, samples):
    inst = make_inst()
    errors = []
    params = {
        "trigger_source": "software",
        "cb_samples": 64,
        "samples": samples,
        "rate": 1.0e6,
        "finite": True,
    }
    monkeypatch.setattr(inst, "fail_with", lambda msg: errors.append(msg) or False)

    assert not inst.configure_triggered(params)
    assert errors


def test_configure_triggered_infinite_uses_zero_loops(monkeypatch):
    inst = make_inst({"notify_alignment_bytes": 1})
    card, transfer = configure_triggered(inst, monkeypatch, finite=False)

    assert card.loop_count == 0
    assert not hasattr(transfer, "transfer_samples")


def test_configure_triggered_finite_multi_counts_output_segments(monkeypatch):
    inst = make_inst({"notify_alignment_bytes": 1})
    card, transfer = configure_triggered(inst, monkeypatch)

    assert card.mode == DummySpcm.SPC_REC_FIFO_MULTI
    assert card.loop_count == 6
    assert transfer.transfer_samples == 192


def test_configure_triggered_finite_average_excludes_average_factor(monkeypatch):
    inst = make_inst({"notify_alignment_bytes": 1})
    card, transfer = configure_triggered(
        inst, monkeypatch, block_reduce_factor=5, hardware_average=True
    )

    assert card.mode == DummySpcm.SPC_REC_FIFO_AVERAGE
    assert card.loop_count == 6
    assert transfer.transfer_samples == 192


def test_configure_triggered_finite_multi_includes_software_block_factor(monkeypatch):
    inst = make_inst({"notify_alignment_bytes": 1})
    card, transfer = configure_triggered(
        inst, monkeypatch, block_reduce_factor=3, hardware_average=False
    )

    assert card.loop_count == 18
    assert transfer.transfer_samples == 576


def test_finite_notify_samples_is_aligned_exact_divisor():
    inst = make_inst({"notify_alignment_bytes": 256})
    inst._transfer = DummyTransfer(bytes_per_sample=2)

    assert inst._finite_notify_samples(64, 256, 32) == 128


def test_finite_notify_samples_rejects_transfer_without_valid_divisor():
    inst = make_inst({"notify_alignment_bytes": 256})
    inst._transfer = DummyTransfer(bytes_per_sample=2)

    with pytest.raises(ValueError, match="no valid notify size"):
        inst._finite_notify_samples(64, 192, 32)


def test_configure_triggered_increases_buffer_to_finite_notify_size(monkeypatch):
    inst = make_inst({"notify_alignment_bytes": 256})

    _card, transfer = configure_triggered(inst, monkeypatch, samples=256, buffer_size=64)

    assert transfer.notified == 128
    assert inst._buffer_samples == 128
