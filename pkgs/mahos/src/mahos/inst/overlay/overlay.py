#!/usr/bin/env python3

"""
Base class InstrumentOverlay for the instrument overlay.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from mahos.inst.instrument import Instrument
from mahos.util.conv import args_to_list


class InstrumentOverlay(Instrument):
    """Base class for InstrumentOverlay.

    InstrumentOverlay provides a way to define a ``virtual instrument``
    that consists of multiple instruments.
    The role is similar to the meas (measurement) layer nodes; however,
    overlays run in the same process/thread as each instrument.
    Thus, procedures should be implemented as overlays
    when they need strictly synchronous behavior or the best performance (in terms of latency).
    This is also useful for application-specific
    parameterization or fundamental modification of an instrument.

    InstrumentOverlay is accessed by the measurement layer or custom code
    through the same interface as an instrument (usually via instrument :term:`RPC`).

    Instruments should be registered during initialization
    by calling :meth:`add_instruments` in inherited classes.

    """

    def __init__(self, name: str, conf: dict | None = None, prefix: str | None = None):
        Instrument.__init__(self, name, conf, prefix)
        self._instruments: list[Instrument] = []

    def add_instruments(self, *insts: Instrument | None):
        """Add instruments. If None is contained, it is silently ignored."""

        self._instruments.extend([i for i in args_to_list(insts) if i is not None])

    def is_closed(self) -> bool:
        if self._closed:
            self.logger.error("Already closed. Skipping operation.")
            return True
        for inst in self._instruments:
            if inst._closed:
                msg = f"Dependent Instrument {inst.full_name()} is already closed."
                msg += " Skipping operation."
                self.logger.error(msg)
                return True
        return False
