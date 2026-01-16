#!/usr/bin/env python3

"""
Laser module.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from mahos.inst.visa_instrument import VisaInstrument
from mahos.msgs import param_msgs as P


class Hubner_Cobolt(VisaInstrument):
    """Hubner Cobolt Laser."""

    _FAULT_CODES = {
        0: "No fault",
        1: "Temperature error",
        3: "Open interlock",
        4: "Constant power fault",
    }

    def __init__(self, name, conf, prefix=None):
        if "write_termination" not in conf:
            conf["write_termination"] = "\r"
        if "read_termination" not in conf:
            conf["read_termination"] = "\r\n"
        if "baud_rate" not in conf:
            conf["baud_rate"] = 115_200

        # Force disable *IDN? because it's not supported
        conf["query_idn"] = False

        VisaInstrument.__init__(self, name, conf, prefix=prefix)

        mn = self.get_model_number()
        sn = self.get_serial_number()
        self.logger.info(f"Model: {mn} Serial: {sn}")

    def get_model_number(self) -> str:
        """Get model number string."""

        return self.inst.query("glm?")

    def get_serial_number(self) -> str:
        """Get serial number string."""

        return self.inst.query("sn?")

    def get_hours(self) -> float:
        """Get operation hours."""

        ans = self.inst.query("hrs?")
        try:
            return float(ans)
        except ValueError:
            self.logger.exception(f"Unexpected reply to hrs?: {ans}")
            return -1.0

    def get_enable(self) -> bool:
        """get if the laser is turned on."""

        return self.inst.query("l?") == "1"

    def set_enable(self, on: bool) -> bool:
        """set laser enable."""

        if on:
            self.logger.info("Turning on the laser.")
            return self.inst.query("@cob1") == "OK"
        else:
            self.logger.info("Turning off the laser.")
            return self.inst.query("l0") == "OK"

    def get_interlock(self) -> bool:
        """get the interlock state. True means interlock is closed and ready to go."""

        return self.inst.query("ilk?") == "0"

    def get_fault(self) -> int:
        """get the fault state."""

        ans = self.inst.query("f?")
        try:
            code = int(ans)
        except ValueError:
            self.logger.exception(f"Unexpected reply to f?: {ans}")
            return -1

        if not code:
            # code == 0 means no fault.
            return code

        if code in self._FAULT_CODES:
            msg = self._FAULT_CODES[code]
            self.logger.error(f"Fault {code}: {msg}")
        else:
            self.logger.error(f"Unexpected fault code: {code}")
        return code

    def clear_fault(self) -> bool:
        return self.inst.query("cf") == "OK"

    def get_actual_current(self) -> float:
        ans = self.inst.query("i?")
        try:
            return float(ans)
        except ValueError:
            self.logger.exception(f"Unexpected reply to i?: {ans}")
            return 0.0

    def get_power(self) -> float:
        """Get power set point in W."""

        ans = self.inst.query("p?")
        try:
            return float(ans)
        except ValueError:
            self.logger.exception(f"Unexpected reply to p?: {ans}")
            return 0.0

    def set_power(self, power_W: float) -> bool:
        """Set power set point in W."""

        return self.inst.query(f"p {power_W:.12f}") == "OK"

    def get_actual_power(self):
        """Get actual power in W."""

        ans = self.inst.query("pa?")
        try:
            return float(ans)
        except ValueError:
            self.logger.exception(f"Unexpected reply to p?: {ans}")
            return 0.0

    def set_control_mode(self, const_power: bool) -> bool:
        if const_power:
            self.logger.info("Constant power mode.")
            return self.inst.query("cp") == "OK"
        else:
            self.logger.info("Constant current mode.")
            return self.inst.query("ci") == "OK"

    # Standard API

    def start(self, label: str = "") -> bool:
        return self.set_enable(True)

    def stop(self, label: str = "") -> bool:
        return self.set_enable(False)

    def get_param_dict_labels(self) -> list[str]:
        return [""]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue]:
        d = P.ParamDict(
            power=P.FloatParam(
                self.get_power(), minimum=0.0, unit="W", SI_prefix=True, doc="Power Setpoint"
            ),
            # read only params
            actual_power=P.FloatParam(
                self.get_actual_power(),
                read_only=True,
                unit="W",
                SI_prefix=True,
                doc="Measured Power",
            ),
            actual_current=P.FloatParam(
                self.get_actual_current(),
                read_only=True,
                unit="A",
                SI_prefix=True,
                doc="Measured Current",
            ),
            hours=P.FloatParam(self.get_hours(), read_only=True, doc="Operation hours"),
            fault=P.IntParam(self.get_fault(), read_only=True, doc="Fault status"),
            interlock=P.BoolParam(
                self.get_interlock(),
                read_only=True,
                doc="Interlock status (True: closed)",
            ),
        )
        return d

    def configure(self, params: dict, label: str = "") -> bool:
        ps = P.unwrap(params)
        return self.set_power(ps["power"])
