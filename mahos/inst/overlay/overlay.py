#!/usr/bin/env python3

"""
Base class InstrumentOverlay for the instrument overlay.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from ..instrument import Instrument
from ...util.conv import args_to_list


class InstrumentOverlay(Instrument):
    """Base class for InstrumentOverlay.

    InstrumentOverlay provides a way to define `virtual instrument`
    that consists of multiple instruments.
    The role is similar to meas layer; however,
    overlay works on the same process / thread with each instrument.
    Thus, procedures should be implemented as overlay
    when it needs strictly synchronous behaviour or the best performance (in terms of latency).
    It is also useful to define application-specific
    parametrization or fundamental modification to an instrument.

    InstOverlay is accessed by meas layer or custom codes
    via same interface with instrument (usually via Instrument :term:`RPC`).

    """

    def __init__(self, name: str, conf: dict | None = None, prefix: str | None = None):
        """Init Instrument and internal instrument list (_instruments).

        Instruments should be added on initialization by add_instruments() in inherited class.

        """

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
