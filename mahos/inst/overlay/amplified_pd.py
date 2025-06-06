#!/usr/bin/env python3

"""
Overlay for Photo Detector + Programmable Amplifier.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np

from .overlay import InstrumentOverlay
from ...msgs import param_msgs as P
from ..lockin import LI5640
from ..pd import LUCI_OE200, AnalogPD, LockinAnalogPD


class AnalogPDMM(InstrumentOverlay):
    """Generic Photo Detector based on DMM with fixed amplifier gain and unit.

    :param unit: (default: V) unit after conversion.
    :type unit: str
    :param gain: (default: 1.0) the fixed gain in [unit] / V.
        Example) when a transimpedance amp with 1000 V / A is used for a photo diode and
        the unit is 'A', gain should be set 1000.
    :type gain: float

    """

    def __init__(self, name, conf, prefix=None):
        InstrumentOverlay.__init__(self, name, conf=conf, prefix=prefix)

        self.dmm = self.conf["dmm"]
        self.dmm_label = self.conf.get("dmm_label", "dcv")

        self.gain = self.conf.get("gain", 1.0)
        self.unit = self.conf.get("unit", "V")

    def get_param_dict_labels(self) -> list[str]:
        return ["pd"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        if label == "pd":
            return self.dmm.get_param_dict(self.dmm_label)

    def configure(self, params: dict, label: str = "") -> bool:
        p = P.unwrap(params)
        return self.dmm.configure(p, label=self.dmm_label)

    def get_data(self) -> float:
        return self.dmm.get("data", label=self.dmm_label) / self.gain

    def set(self, key: str, value=None, label: str = "") -> bool:
        key = key.lower()
        if key == "gain":
            if isinstance(value, (float, int, np.floating, np.integer)):
                self.gain = float(value)
                return True
            else:
                return self.fail_with("gain must be a number (float or int)")
        elif key == "unit":
            self.unit = str(value)
            return True
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None

    def get(self, key: str, args=None, label: str = ""):
        if key == "data":
            return self.get_data()
        elif key == "unit":
            return self.unit
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None

    def start(self, label: str = "") -> bool:
        return self.dmm.start(self.dmm_label)

    def stop(self, label: str = "") -> bool:
        return self.dmm.stop(self.dmm_label)


class LockinAnalogPDMM(InstrumentOverlay):
    """Generic Photo Detector based on DMM with fixed amplifier gain and unit.

    :param unit: (default: V) unit after conversion.
    :type unit: str
    :param gain: (default: 1.0) the fixed gain in [unit] / V.
        Example) when a transimpedance amp with 1000 V / A is used for a photo diode and
        the unit is 'A', gain should be set 1000.
    :type gain: float

    """

    def __init__(self, name, conf, prefix=None):
        InstrumentOverlay.__init__(self, name, conf=conf, prefix=prefix)

        self.dmm = self.conf["dmm"]
        self.dmm_labelX = self.conf.get("dmm_labelX", "ch1_dcv")
        self.dmm_labelY = self.conf.get("dmm_labelY", "ch2_dcv")

        self.gain = self.conf.get("gain", 1.0)
        self.unit = self.conf.get("unit", "V")

    def get_param_dict_labels(self) -> list[str]:
        return ["pd"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        if label == "pd":
            return P.ParamDict(
                X=self.dmm.get_param_dict(self.dmm_labelX),
                Y=self.dmm.get_param_dict(self.dmm_labelY),
            )

    def configure(self, params: dict, label: str = "") -> bool:
        pX = P.unwrap(params["X"])
        pY = P.unwrap(params["Y"])
        return self.dmm.configure(pX, label=self.dmm_labelX) and self.dmm.configure(
            pY, label=self.dmm_labelY
        )

    def get_data(self) -> np.cdouble:
        re, im = self.dmm.get_all_data()
        return np.cdouble(re + 1.0j * im) / self.gain

    def set(self, key: str, value=None, label: str = "") -> bool:
        key = key.lower()
        if key == "gain":
            if isinstance(value, (float, int, np.floating, np.integer)):
                self.gain = float(value)
                return True
            else:
                return self.fail_with("gain must be a number (float or int)")
        elif key == "unit":
            self.unit = str(value)
            return True
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None

    def get(self, key: str, args=None, label: str = ""):
        if key == "data":
            return self.get_data()
        elif key == "unit":
            return self.unit
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None

    def start(self, label: str = "") -> bool:
        return self.dmm.start(self.dmm_labelX) and self.dmm.start(self.dmm_labelY)

    def stop(self, label: str = "") -> bool:
        return self.dmm.stop(self.dmm_labelX) and self.dmm.stop(self.dmm_labelY)


class _LI5640Mixin(object):
    def init_lockin(self):
        self.li5640.set_data1(LI5640.Data1.X)
        self.li5640.set_data2(LI5640.Data2.Y)
        self.li5640.set_Xoffset_enable(False)
        self.li5640.set_Yoffset_enable(False)
        self.li5640.set_data_normalization(LI5640.DataNormalization.OFF)

        #  These settings must not be changed afterwards.
        self.li5640.lock_params(
            ["data1", "data2", "Xoffset_enable", "Yoffset_enable", "data_normalization"]
        )

    def update_gain(self) -> tuple[float, float]:
        #  It is not perfect to memoise the param values at LI5640 setters
        #  due to auto-setting or local operation.
        #  Fetch the necessary parameters on our timing.

        volt_sens = self.li5640.get_volt_sensitivity_float()
        data1_expand = self.li5640.get_data1_expand()
        data2_expand = self.li5640.get_data2_expand()

        v1_gain = data1_expand * 10.0 / volt_sens
        v2_gain = data2_expand * 10.0 / volt_sens
        self.gain = v1_gain, v2_gain
        self.total_gain = v1_gain * self.pd.gain, v2_gain * self.pd.gain
        tg = self.total_gain
        self.logger.info(f"Current total gain: {tg[0]:.2e}, {tg[1]:.2e} V/{self.pd.unit}")
        return self.gain


class LockinAnalogPD_LI5640(InstrumentOverlay, _LI5640Mixin):
    """Generic (fixed gain) Photoreceiver and with LI5640 Lockin & DAQ AnalogIn.

    :param li5640: a LI5640 instance
    :type li5640: LI5640
    :param pd: a LockinAnalogPD instance.
    :type pd: LockinAnalogPD

    """

    def __init__(self, name, conf, prefix=None):
        InstrumentOverlay.__init__(self, name, conf=conf, prefix=prefix)

        self.li5640: LI5640 = self.conf.get("li5640")
        self.pd: LockinAnalogPD = self.conf.get("pd")
        self.add_instruments(self.li5640, self.pd)

        self.init_lockin()
        self.update_gain()

    # LockinAnalogPD wrappers / compatible interfaces

    def _convert_data(
        self, data: np.ndarray | np.cdouble | tuple[np.ndarray, float] | None
    ) -> np.ndarray | np.cdouble | tuple[np.ndarray, float] | None:
        if data is None:
            return None

        gain_r, gain_i = self.gain

        if isinstance(data, np.cdouble):
            # read-on-demand
            return np.cdouble(data.real / gain_r + 1.0j * data.imag / gain_i)
        elif isinstance(data, tuple):
            #  stamped clock-mode
            data[0].real /= gain_r
            data[0].imag /= gain_i
            return data
        else:
            # ndarray, buffered read
            data.real /= gain_r
            data.imag /= gain_i
            return data

    def _convert_all_data(
        self, data: list[np.ndarray | tuple[np.ndarray, float]] | None
    ) -> list[np.ndarray | tuple[np.ndarray, float]] | None:
        if data is None:
            return None
        return [self._convert_data(d) for d in data]

    # Methods used by confocal_scanner

    def pop_block(
        self,
    ) -> np.ndarray | tuple[np.ndarray | float]:
        return self._convert_data(self.pd.pop_block())

    def get_max_rate(self) -> float | None:
        return self.pd.get_max_rate()

    # Standard API

    def set(self, key: str, value=None, label: str = "") -> bool:
        # no set() key for pd

        success = self.li5640.set(key, value)
        #  set() may change the gain.
        self.update_gain()
        return success

    def start(self, label: str = "") -> bool:
        return self.pd.start()

    def stop(self, label: str = "") -> bool:
        return self.pd.stop()

    def get(self, key: str, args=None, label: str = ""):
        if key == "data":
            return self._convert_data(self.pd.get(key, args))
        elif key == "all_data":
            return self._convert_all_data(self.pd.get(key, args))
        elif key == "unit":
            return self.pd.unit
        elif key == "gain":
            return self.total_gain
        else:
            return self.li5640.get(key, args)

    def get_param_dict_labels(self) -> list[str]:
        return ["li5640"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        if label == "li5640":
            return self.li5640.get_param_dict(label)
        else:
            return self.pd.get_param_dict(label)

    def configure(self, params: dict, label: str = "") -> bool:
        if label == "li5640":
            success = self.li5640.configure(params, label)
            #  configure() may change the gain.
            self.update_gain()
            return success
        else:
            #  update the gain with PD configuration so as to secure the correct gain
            #  before subsequent (clock_mode) measurement.
            self.update_gain()
            return self.pd.configure(params, label)


class LockinAnalogPDMM_LI5640(InstrumentOverlay, _LI5640Mixin):
    """Generic (fixed gain) Photoreceiver and with LI5640 Lockin & DMM.

    :param li5640: a LI5640 instance
    :type li5640: LI5640
    :param pd: a LockinAnalogPDMM instance.
    :type pd: LockinAnalogPDMM

    """

    def __init__(self, name, conf, prefix=None):
        InstrumentOverlay.__init__(self, name, conf=conf, prefix=prefix)

        self.li5640: LI5640 = self.conf.get("li5640")
        self.pd: LockinAnalogPDMM = self.conf.get("pd")
        self.add_instruments(self.li5640, self.pd)

        self.init_lockin()
        self.update_gain()

    def _convert(self, data):
        gain_r, gain_i = self.gain
        return np.cdouble(data.real / gain_r + 1.0j * data.imag / gain_i)

    def get_data(self) -> np.cdouble:
        return self._convert(self.pd.get_data())

    # Standard API

    def set(self, key: str, value=None, label: str = "") -> bool:
        # no set() key for pd

        success = self.li5640.set(key, value)
        #  set() may change the gain.
        self.update_gain()
        return success

    def start(self, label: str = "") -> bool:
        return self.pd.start()

    def stop(self, label: str = "") -> bool:
        return self.pd.stop()

    def get(self, key: str, args=None, label: str = ""):
        if key == "data":
            return self._convert_data(self.pd.get(key, args))
        elif key == "unit":
            return self.pd.unit
        elif key == "gain":
            return self.total_gain
        else:
            return self.li5640.get(key, args)

    def get_param_dict_labels(self) -> list[str]:
        return ["li5640"] + self.pd.get_param_dict_labels()

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        if label == "li5640":
            return self.li5640.get_param_dict(label)
        else:
            return self.pd.get_param_dict(label)

    def configure(self, params: dict, label: str = "") -> bool:
        if label == "li5640":
            success = self.li5640.configure(params, label)
            #  configure() may change the gain.
            self.update_gain()
            return success
        else:
            #  update the gain with PD configuration so as to secure the correct gain
            #  before subsequent (clock_mode) measurement.
            self.update_gain()
            return self.pd.configure(params, label)


class OE200_AI(InstrumentOverlay):
    """FEMTO Messtechnik OE-200 Variable Gain Photoreceiver with DAQ AnalogIn.

    :param luci: a LUCI_OE200 instance
    :type luci: LUCI_OE200
    :param pd: a AnalogPD instance. gain should be 1.
    :type pd: AnalogPD

    """

    def __init__(self, name, conf, prefix=None):
        InstrumentOverlay.__init__(self, name, conf=conf, prefix=prefix)

        self.luci: LUCI_OE200 = self.conf.get("luci")
        self.pd: AnalogPD = self.conf.get("pd")
        if len(self.pd.lines) != 1:
            raise ValueError("len(lines) of pd must be 1.")

        self.add_instruments(self.luci, self.pd)

    # AnalogPD wrappers / compatible interfaces

    def _convert_data(
        self, data: np.ndarray | np.float64 | tuple[np.ndarray, float] | None
    ) -> np.ndarray | np.float64 | tuple[np.ndarray, float] | None:
        if data is None:
            return None

        if isinstance(data, tuple):
            #  stamped clock-mode
            return data[0] / self.luci.gain, data[1]

        # np.ndarray (non-stamped clock-mode) | np.float64 (read-on-demand)
        return data / self.luci.gain

    def _convert_all_data(
        self, data: list[np.ndarray | tuple[np.ndarray, float]] | None
    ) -> list[np.ndarray | tuple[np.ndarray, float]] | None:
        if data is None:
            return None
        return [self._convert_data(d) for d in data]

    # Methods used by confocal_scanner
    def pop_block(
        self,
    ) -> np.ndarray | tuple[np.ndarray | float]:
        return self._convert_data(self.pd.pop_block())

    def get_max_rate(self) -> float | None:
        return self.pd.get_max_rate()

    # Standard API

    def set(self, key: str, value=None, label: str = "") -> bool:
        # no set() key for AnalogIn
        return self.luci.set(key, value)

    def get(self, key: str, args=None, label: str = ""):
        if key == "data":
            return self._convert_data(self.pd.get(key, args))
        elif key == "all_data":
            return self._convert_all_data(self.pd.get(key, args))
        elif key == "unit":
            return "W"
        else:
            return self.luci.get(key, args)

    def get_param_dict_labels(self) -> list[str]:
        return ["luci"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        """Get ParamDict for `label`."""

        if label == "luci":
            return self.luci.get_param_dict(label)
        else:
            return self.pd.get_param_dict(label)

    def configure(self, params: dict, label: str = "") -> bool:
        if label == "luci":
            return self.luci.configure(params, label)
        else:
            return self.pd.configure(params, label)

    def start(self, label: str = "") -> bool:
        return self.pd.start()

    def stop(self, label: str = "") -> bool:
        return self.pd.stop()


class OE200_LI5640_AI(InstrumentOverlay):
    """FEMTO Messtechnik OE-200 Variable Gain Photoreceiver and with LI5640 Lockin & DAQ AnalogIn.

    :param luci: a LUCI_OE200 instance
    :type luci: LUCI_OE200
    :param li5640: a LI5640 instance
    :type li5640: LI5640
    :param pd: a LockinAnalogPD instance. gain should be 1.
    :type pd: LockinAnalogPD

    """

    def __init__(self, name, conf, prefix=None):
        InstrumentOverlay.__init__(self, name, conf=conf, prefix=prefix)

        self.luci: LUCI_OE200 = self.conf.get("luci")
        self.li5640: LI5640 = self.conf.get("li5640")
        self.pd: LockinAnalogPD = self.conf.get("pd")
        self.add_instruments(self.luci, self.li5640, self.pd)

        self.init_lockin()
        self.update_gain()

    def init_lockin(self):
        self.li5640.set_data1(LI5640.Data1.X)
        self.li5640.set_data2(LI5640.Data2.Y)
        self.li5640.set_Xoffset_enable(False)
        self.li5640.set_Yoffset_enable(False)
        self.li5640.set_data_normalization(LI5640.DataNormalization.OFF)

        #  These settings must not be changed afterwards.
        self.li5640.lock_params(
            ["data1", "data2", "Xoffset_enable", "Yoffset_enable", "data_normalization"]
        )

    def update_gain(self) -> tuple[float, float]:
        #  It is not perfect to memoise the param values at LI5640 setters
        #  due to auto-setting or local operation.
        #  Fetch the necessary parameters on our timing.

        volt_sens = self.li5640.get_volt_sensitivity_float()
        data1_expand = self.li5640.get_data1_expand()
        data2_expand = self.li5640.get_data2_expand()

        v1_gain = data1_expand * 10.0 / volt_sens
        v2_gain = data2_expand * 10.0 / volt_sens
        self.gain = v1_gain * self.luci.gain, v2_gain * self.luci.gain
        self.logger.info(f"Current total gain: {self.gain[0]:.2e}, {self.gain[1]:.2e} V/W")
        return self.gain

    # LockinAnalogPD wrappers / compatible interfaces

    def _convert_data(
        self, data: np.ndarray | np.cdouble | tuple[np.ndarray, float] | None
    ) -> np.ndarray | np.cdouble | tuple[np.ndarray, float] | None:
        if data is None:
            return None

        gain_r, gain_i = self.gain

        if isinstance(data, np.cdouble):
            # read-on-demand
            return np.cdouble(data.real / gain_r + 1.0j * data.imag / gain_i)
        elif isinstance(data, tuple):
            #  stamped clock-mode
            data[0].real /= gain_r
            data[0].imag /= gain_i
            return data
        else:
            # ndarray, buffered read
            data.real /= gain_r
            data.imag /= gain_i
            return data

    def _convert_all_data(
        self, data: list[np.ndarray | tuple[np.ndarray, float]] | None
    ) -> list[np.ndarray | tuple[np.ndarray, float]] | None:
        if data is None:
            return None
        return [self._convert_data(d) for d in data]

    # Methods used by confocal_scanner

    def pop_block(
        self,
    ) -> np.ndarray | tuple[np.ndarray | float]:
        return self._convert_data(self.pd.pop_block())

    def get_max_rate(self) -> float | None:
        return self.pd.get_max_rate()

    # Standard API

    def set(self, key: str, value=None, label: str = "") -> bool:
        # no set() key for pd
        key = key.lower()
        if key in ("led", "gain", "coupling"):
            return self.luci.set(key, value)
        else:
            success = self.li5640.set(key, value)
            #  set() may change the gain.
            self.update_gain()
            return success

    def get(self, key: str, args=None, label: str = ""):
        if key == "data":
            return self._convert_data(self.pd.get(key, args))
        elif key == "all_data":
            return self._convert_all_data(self.pd.get(key, args))
        elif key == "unit":
            return "W"
        elif key == "gain":
            return self.gain
        elif key in ("devices", "id", "pin", "product"):
            return self.luci.get(key, args)
        else:
            return self.li5640.get(key, args)

    def get_param_dict_labels(self) -> list[str]:
        return ["luci", "li5640"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        """Get ParamDict for `label`."""

        if label == "luci":
            return self.luci.get_param_dict(label)
        elif label == "li5640":
            return self.li5640.get_param_dict(label)
        else:
            return self.pd.get_param_dict(label)

    def configure(self, params: dict, label: str = "") -> bool:
        if label == "luci":
            return self.luci.configure(params, label)
        elif label == "li5640":
            success = self.li5640.configure(params, label)
            #  configure() may change the gain.
            self.update_gain()
            return success
        else:
            #  update the gain with PD configuration so as to secure the correct gain
            #  before subsequent (clock_mode) measurement.
            self.update_gain()
            return self.pd.configure(params, label)

    def start(self, label: str = "") -> bool:
        return self.pd.start()

    def stop(self, label: str = "") -> bool:
        return self.pd.stop()
