#!/usr/bin/env python3

"""Free-period splitting for the Pulse ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import math

from mahos.util.conf import ConfAccessorMixin
from mahos_dq.meas.podmr_generator import generator_kernel as K


class IntervalSplitter(ConfAccessorMixin):
    """Select fractional or fixed-head splitting from pulser configuration.

    Pulse ODMR pattern generators split each free period into a head and a tail, and switch
    the MW phase at the boundary. Two splitting modes are available.

    Fractional splitting (default) splits a period of T ticks into ``(T // F, T - T // F)``
    with the fraction factor F (``split_fraction``). Larger F results in a "quicker start" of
    the phase modulation (depending on hardware, its response may be a bit slow).

    Fixed-head splitting is selected by configuring ``split_head``. The head is a fixed
    duration, rounded to the nearest tick at the original clock. Frequency reduction preserves
    this duration exactly, and may therefore be limited by it. The tail is the remaining
    portion, and must be at least ``min_split_tail`` (rounded upward at the effective clock).
    A ``ValueError`` is raised for any free period that is too short, which usually rejects
    the whole sweep (e.g. a tau sweep starting near zero).

    :param split_fraction: (default: 4) fraction factor F for fractional splitting.
        Disregarded (with a warning) when ``split_head`` is configured.
    :type split_fraction: int
    :param split_head: fixed head duration in seconds (e.g. ``20e-9`` for 20 ns).
        If absent, fractional splitting is used.
    :type split_head: float
    :param min_split_tail: (default: 0) minimum tail duration in seconds for fixed-head
        splitting. Disregarded (with a warning) when ``split_head`` is not configured.
    :type min_split_tail: float

    """

    def __init__(self, conf: dict, warn_fn=None):
        self.conf = conf
        self.head = self._conf_nonneg_num("split_head") if "split_head" in conf else None
        self.min_tail = self._conf_nonneg_num("min_split_tail", 0)
        self.fraction = self._conf_pos_int("split_fraction", 4)
        if warn_fn is not None:
            if self.head is not None and "split_fraction" in conf:
                warn_fn("split_fraction is disregarded because split_head is configured.")
            elif self.head is None and "min_split_tail" in conf:
                warn_fn("min_split_tail is disregarded because split_head is not configured.")

    def ticks_to_preserve(self, freq: float) -> tuple[int, ...]:
        """Return additional durations that must survive clock reduction exactly."""

        return () if self.head is None else (round(self.head * freq),)

    def split(self, value: int, original_freq: float, freq: float) -> tuple[int, int]:
        """Split integer ticks, rejecting intervals with an insufficient tail."""

        if self.head is None:
            return K._split_int(value, self.fraction)
        # Quantize at the original clock, then reduce exactly by the integer clock ratio.
        head0 = round(self.head * original_freq)
        ratio = round(original_freq / freq)
        if head0 % ratio:
            raise ValueError(
                f"split_head ({head0} ticks at {original_freq:g} Hz) is not representable at "
                f"{freq:g} Hz. Round pulses with PatternGenerator._round_pulses() so the head "
                "is preserved during frequency reduction."
            )
        head = head0 // ratio
        # Allow one ULP of multiplication noise above an integer tick boundary.
        minimum = math.ceil(math.nextafter(self.min_tail * freq, -math.inf))
        tail = value - head
        if tail < minimum:
            raise ValueError(
                f"Cannot split interval {value} ticks at {freq:g} Hz: it is shorter than "
                f"split_head ({head} ticks) + min_split_tail ({minimum} ticks)."
            )
        return head, tail
