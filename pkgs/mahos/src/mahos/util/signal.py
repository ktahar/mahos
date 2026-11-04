#!/usr/bin/env python3

"""
Signal processing utility module.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import numpy.typing as npt

import mahos.util.validation as V


def real_fft(
    xdata: npt.ArrayLike, ydata: npt.ArrayLike, remove_dc: bool = True
) -> tuple[npt.NDArray, npt.NDArray]:
    """Return the single-sided amplitude spectrum of a real-valued signal.

    Assumes xdata is uniformly spaced. Frequencies are in inverse units of
    xdata, and amplitudes have the same units as ydata.

    FFT magnitudes are normalized by the number of samples and doubled to
    account for the omitted negative-frequency components.
    DC and, for even sample counts, the Nyquist component are not doubled
    because they have no separate negative-frequency counterparts.

    For a sinusoid at an FFT bin frequency strictly between DC and Nyquist,
    the corresponding amplitude equals its peak amplitude (not RMS).

    If remove_dc is True, the returned DC amplitude is set to zero.

    """

    from scipy import fft

    N = len(xdata)
    if N != len(ydata) or N < 2:
        raise ValueError("xdata and ydata must have the same length >= 2")

    freq = fft.rfftfreq(N, abs(xdata[1] - xdata[0]))
    amp = np.abs(fft.rfft(ydata)) / N
    # scale values by 2 where negative counterpart exists.
    if N % 2 == 0:
        amp[1:-1] *= 2  # exclude DC and Nyquist
    else:
        amp[1:] *= 2  # exclude DC
    if remove_dc:
        amp[0] = 0

    return freq, amp


def real_fftfreq(xdata: npt.ArrayLike) -> npt.NDArray:
    """Return only frequency space part of ``real_fft``."""

    from scipy import fft

    return fft.rfftfreq(len(xdata), abs(xdata[1] - xdata[0]))


def power_spectral_density(
    data: npt.ArrayLike,
    sampling_freq: float,
    freq_spacing: float,
    *,
    window="hann",
    detrend="constant",
    average="mean",
    noverlap=None,
) -> tuple[npt.NDArray, npt.NDArray]:
    """Estimate a real signal's one-sided PSD using Welch's method.

    This is a thin wrapper for ``scipy.signal.welch`` with frequency-bin spacing
    (frequency resolution) control with ``freq_spacing``.
    Smaller ``freq_spacing`` gives longer segments and fewer averages, subject to clipping.

    See ``scipy.signal.welch`` for passed-through keyword arguments
    "window", "detrend", "average", and "noverlap".

    :param data: One-dimensional, finite, real-valued, uniformly sampled signal with
        at least two samples.
    :param sampling_freq: Finite, positive sampling frequency in Hz.
    :param freq_spacing: Finite, positive target frequency-bin spacing in Hz.
        The segment length is ``round(sampling_freq / freq_spacing)``, clipped to
        the range from two samples to the full record length.
    :returns: ``(freq, density)``. Frequencies are in Hz and include DC. Actual spacing is
        ``sampling_freq / nperseg`` and may differ from the requested spacing due to rounding
        or clipping. For a signal with unit U, the one-sided PSD has units ``U**2/Hz``;
        its square root is ASD in ``U/sqrt(Hz)``.
    :rtype: tuple[numpy.ndarray, numpy.ndarray]
    :raises ValueError: If data is not a one-dimensional finite real signal with at least two
        samples, either frequency argument is nonfinite or nonpositive,
        or an option is invalid for ``scipy.signal.welch``.

    """

    from scipy import signal

    data = np.asarray(data)
    if data.ndim != 1 or len(data) < 2 or not np.isrealobj(data) or not np.all(np.isfinite(data)):
        raise ValueError("data must be a 1D finite real signal with at least two samples")
    if not np.isfinite(sampling_freq) or sampling_freq <= 0:
        raise ValueError("sampling_freq must be finite and positive")
    if not np.isfinite(freq_spacing) or freq_spacing <= 0:
        raise ValueError("freq_spacing must be finite and positive")

    nperseg = round(sampling_freq / freq_spacing)
    nperseg = max(2, min(nperseg, len(data)))
    freq, density = signal.welch(
        data,
        fs=sampling_freq,
        nperseg=nperseg,
        window=window,
        detrend=detrend,
        average=average,
        noverlap=noverlap,
        nfft=None,
        return_onesided=True,
        scaling="density",
    )
    return freq, density


def bin_power_spectral_density(
    freq: npt.ArrayLike, psd: npt.ArrayLike, bins: int
) -> tuple[npt.NDArray, npt.NDArray, npt.NDArray, npt.NDArray]:
    """Reduce a PSD to mean and peak values in logarithmic frequency bins.

    Bins include their left edge and exclude their right edge, except that the
    final bin includes the highest input frequency. Empty bins are omitted.
    Arithmetic means estimate band-average density for uniformly spaced input
    frequencies, such as Welch output; irregular spacing requires weighting
    for that interpretation. These values are densities, not integrated powers.
    Peak values describe an upper envelope and depend on the number of input points per bin.

    :param freq: One-dimensional, finite, strictly positive frequencies in strictly
        increasing order. Remove the DC component before calling this function.
    :param psd: One-dimensional, finite, nonnegative power spectral densities with the
        same length as ``freq``. For an input signal with unit U and frequencies
        in Hz, these values have units ``U**2/Hz``.
    :param bins: Positive integer specifying the requested number of logarithmically spaced bins.
        If data length is smaller than or equal to ``bins``, reduction is skipped.
    :returns: ``(mean_freq, mean_psd, peak_freq, peak_psd)``, equally sized arrays with one entry
        per nonempty bin. Mean frequencies are bin geometric centers; mean PSDs are arithmetic
        means of the input densities. Peak frequencies are the original frequencies of the
        largest PSD in each bin (the first in case of ties). If reduction is skipped,
        both curves use the original frequencies and densities. PSD units are unchanged.
    :raises ValueError: If ``bins`` is not a positive integer.

    """

    V.check_pos_int(bins, "bins")
    freq = np.asarray(freq)
    psd = np.asarray(psd)
    if len(freq) <= bins:
        return freq, psd, freq, psd

    edges = np.geomspace(freq[0], freq[-1], bins + 1)
    boundaries = np.searchsorted(freq, edges)
    boundaries[-1] = len(freq)  # Include the highest frequency.
    mean_frequency, mean_psd, peak_indices = [], [], []
    for i, (start, stop) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        if stop <= start:
            continue
        values = psd[start:stop]
        mean_frequency.append(np.sqrt(edges[i]) * np.sqrt(edges[i + 1]))
        mean_psd.append(np.mean(values))
        peak_indices.append(start + np.argmax(values))
    return (
        np.array(mean_frequency),
        np.array(mean_psd),
        freq[peak_indices],
        psd[peak_indices],
    )


def binned_power_spectral_density(
    data: npt.ArrayLike,
    sampling_freq: float,
    freq_spacing: float,
    bins: int = 3000,
    *,
    window="hann",
    detrend="constant",
    average="mean",
    noverlap=None,
) -> tuple[npt.NDArray, npt.NDArray, npt.NDArray, npt.NDArray]:
    """Estimate a Welch PSD and reduce it to mean and peak values in log bins.

    Wraps ``power_spectral_density`` and ``bin_power_spectral_density``,
    removing DC before binning.
    Nonfinite or negative densities raise an error.

    See ``scipy.signal.welch`` for passed-through keyword arguments
    "window", "detrend", "average", and "noverlap".

    :param data: One-dimensional, finite, real-valued, uniformly sampled signal with
        at least two samples.
    :param sampling_freq: Finite, positive sampling frequency in Hz.
    :param freq_spacing: Finite, positive target Welch frequency-bin spacing in Hz.
        Segment-length rounding and clipping follow ``power_spectral_density``.
    :param bins: Positive integer specifying the requested number of logarithmic output bins.
        This controls output size independently of Welch's frequency spacing.
    :returns: ``(mean_freq, mean_psd, peak_freq, peak_psd)``, as returned by
        ``bin_power_spectral_density``.
        Frequencies are in Hz. For input signal unit U, densities have units ``U**2/Hz``.
        Mean frequencies are bin geometric centers; peak frequencies retain their
        original positions. If binning is unnecessary, both curves use the original
        positive-frequency samples. Each curve contains at most ``bins`` points.
    :raises ValueError: If an argument is invalid for ``power_spectral_density`` or
        ``bin_power_spectral_density``, or the calculated PSD contains nonfinite or negative
        values.

    """

    freq, psd = power_spectral_density(
        data,
        sampling_freq,
        freq_spacing,
        window=window,
        detrend=detrend,
        average=average,
        noverlap=noverlap,
    )
    if not np.all(np.isfinite(psd)) or np.any(psd < 0):
        raise ValueError("calculated PSD must contain only finite, nonnegative values")
    # logspace binning requires positive frequency
    positive = freq > 0
    return bin_power_spectral_density(freq[positive], psd[positive], bins)
