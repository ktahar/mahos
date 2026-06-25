#!/usr/bin/env python3

"""
Spectrum digitizer utility functions.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

SPECTRUM_SEGMENT_SAMPLES_MIN = 32
SPECTRUM_SEGMENT_SAMPLES_BASE = 16


def offset_base_inc(value: int, base: int) -> int:
    """Round ``value`` up to an integer multiple of ``base``."""

    value = int(value)
    base = int(base)
    residual = value % base
    if residual:
        return value + base - residual
    return value


def round_spectrum_segment_samples(samples: int) -> int:
    """Round sample count up to Spectrum multiple-recording segment constraints."""

    samples = max(SPECTRUM_SEGMENT_SAMPLES_MIN, int(samples))
    return offset_base_inc(samples, SPECTRUM_SEGMENT_SAMPLES_BASE)


def valid_spectrum_segment_samples(samples: int) -> bool:
    """Return whether ``samples`` satisfies Spectrum segment-size constraints."""

    samples = int(samples)
    return samples >= SPECTRUM_SEGMENT_SAMPLES_MIN and samples % SPECTRUM_SEGMENT_SAMPLES_BASE == 0


def round_duration_for_spectrum_segment(
    duration: int,
    base: int,
    sample_factor: int,
    sample_divisor: int,
    max_iterations: int = 1_000_000,
) -> tuple[int, int]:
    """Increment ``duration`` by ``base`` until derived segment samples are valid.

    The derived segment samples are ``duration * sample_factor // sample_divisor``.
    This is intended for pulse-sequence builders where increasing the acquisition
    duration is the measurement-side way to satisfy Spectrum's segment-size constraint.

    """

    if sample_factor < 1:
        raise ValueError("sample_factor must be positive.")
    if sample_divisor < 1:
        raise ValueError("sample_divisor must be positive.")

    duration = offset_base_inc(max(1, int(duration)), int(base))
    for _ in range(max_iterations):
        samples = duration * sample_factor // sample_divisor
        if valid_spectrum_segment_samples(samples):
            return duration, samples
        duration += base

    raise ValueError(
        "could not find a Spectrum-compatible duration "
        f"from duration={duration}, base={base}, sample_factor={sample_factor}, "
        f"sample_divisor={sample_divisor}"
    )
