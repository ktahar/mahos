#!/usr/bin/env python3

"""
Tests for mahos.util.signal.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from mahos.util import signal


def test_real_fft_peak():
    freq_hz = 3.0
    n = 100
    xdata = np.linspace(0.0, 1.0, n, endpoint=False)
    ydata = np.sin(2.0 * np.pi * freq_hz * xdata)

    freqs, spec = signal.real_fft(xdata, ydata, remove_dc=True)
    peak = freqs[int(np.argmax(spec))]

    assert peak == pytest.approx(freq_hz)


def test_real_fft_remove_dc():
    n = 64
    xdata = np.linspace(0.0, 1.0, n, endpoint=False)
    ydata = np.ones(n)

    _, spec = signal.real_fft(xdata, ydata, remove_dc=True)

    assert np.allclose(spec, 0.0)


def test_real_fft_length_mismatch():
    with pytest.raises(ValueError):
        signal.real_fft([0.0, 1.0], [1.0])


def test_real_fftfreq():
    xdata = np.linspace(0.0, 1.0, 10, endpoint=False)
    freqs = signal.real_fftfreq(xdata)
    assert len(freqs) == 6
    assert freqs[0] == 0.0


@pytest.mark.parametrize("n", [15, 16])
def test_real_fft_amplitudes(n):
    xdata = np.arange(n) / n
    ydata = 3.0 + 2.0 * np.cos(2.0 * np.pi * (n // 2) * xdata)

    freqs, amplitudes = signal.real_fft(xdata, ydata, remove_dc=False)

    np.testing.assert_allclose(freqs, signal.real_fftfreq(xdata))
    assert len(freqs) == n // 2 + 1
    assert amplitudes[0] == pytest.approx(3.0)
    assert amplitudes[-1] == pytest.approx(2.0)
    np.testing.assert_allclose(amplitudes[1:-1], 0.0, atol=1e-14)


def test_power_spectral_density_sinusoid():
    sampling_freq = 64.0
    data = 3.0 + 2.0 * np.cos(2.0 * np.pi * 8.0 * np.arange(128) / sampling_freq)

    freq, psd = signal.power_spectral_density(data, sampling_freq, 1.0, window="boxcar")

    np.testing.assert_allclose(freq, np.arange(33))
    assert freq[np.argmax(psd)] == 8.0
    assert psd[0] == pytest.approx(0.0, abs=1e-14)
    assert psd[8] == pytest.approx(2.0)
    assert np.sum(psd) * (freq[1] - freq[0]) == pytest.approx(2.0)


@pytest.mark.parametrize("spacing, nperseg", [(3.0, 5), (0.1, 16), (100.0, 2)])
def test_power_spectral_density_spacing(spacing, nperseg):
    freq, psd = signal.power_spectral_density(np.zeros(16), 16.0, spacing)

    np.testing.assert_allclose(freq, np.arange(nperseg // 2 + 1) * 16.0 / nperseg)
    np.testing.assert_array_equal(psd, np.zeros_like(freq))


@pytest.mark.parametrize("value", [0.0, -1.0, np.nan, np.inf])
@pytest.mark.parametrize("argument", ["sampling_freq", "freq_spacing"])
def test_power_spectral_density_invalid_frequency(argument, value):
    kwargs = {"sampling_freq": 16.0, "freq_spacing": 1.0, argument: value}
    with pytest.raises(ValueError, match=argument):
        signal.power_spectral_density(np.zeros(16), **kwargs)


def test_bin_power_spectral_density_boundaries():
    freq = np.array([1.0, 2.0, 3.0, 4.0, 8.0, 16.0])
    psd = np.array([2.0, 6.0, 6.0, 8.0, 10.0, 12.0])

    mean_freq, mean_psd, peak_freq, peak_psd = signal.bin_power_spectral_density(freq, psd, 2)

    np.testing.assert_allclose(mean_freq, [2.0, 8.0])
    np.testing.assert_allclose(mean_psd, [14.0 / 3.0, 10.0])
    np.testing.assert_array_equal(peak_freq, [2.0, 16.0])
    np.testing.assert_array_equal(peak_psd, [6.0, 12.0])


def test_bin_power_spectral_density_empty_bins():
    freq = np.array([1.0, 2.0, 3.0, 4.0, 256.0])
    psd = np.array([2.0, 4.0, 6.0, 8.0, 10.0])

    mean_freq, mean_psd, peak_freq, peak_psd = signal.bin_power_spectral_density(freq, psd, 4)

    np.testing.assert_allclose(mean_freq, [2.0, 8.0, 128.0])
    np.testing.assert_allclose(mean_psd, [4.0, 8.0, 10.0])
    np.testing.assert_array_equal(peak_freq, [3.0, 4.0, 256.0])
    np.testing.assert_array_equal(peak_psd, [6.0, 8.0, 10.0])


@pytest.mark.parametrize("bins", [3, 4])
def test_bin_power_spectral_density_no_reduction(bins):
    freq = np.array([1.0, 2.0, 3.0])
    psd = np.array([2.0, 4.0, 6.0])

    result = signal.bin_power_spectral_density(freq, psd, bins)

    for actual, expected in zip(result, (freq, psd, freq, psd)):
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("bins", [2, 32])
def test_binned_power_spectral_density(bins):
    data = np.arange(32, dtype=float)
    options = dict(window="boxcar", detrend=False, average="median", noverlap=0)
    freq, psd = signal.power_spectral_density(data, 32.0, 2.0, **options)
    expected = signal.bin_power_spectral_density(freq[1:], psd[1:], bins)

    result = signal.binned_power_spectral_density(data, 32.0, 2.0, bins=bins, **options)

    for actual, reference in zip(result, expected):
        np.testing.assert_allclose(actual, reference)
        assert 0 < len(actual) <= bins
    assert np.all(result[0] > 0.0)
    assert np.all(result[2] > 0.0)
