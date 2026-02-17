iv_smu
======

A minimum example of custom measurement suite for simple IV characteristic measurement using an SMU,
based on ``BasicMeas``.

This directory contains following:

- ``iv_msgs.py``: Custom data type definition.
- ``iv_io.py``: I/O for defined data type.
- ``iv.py``: Core measurement logic. Node and Worker.
- ``iv_gui.py``: GUI frontend of the measurement logic.
- ``instruments.py``: Mock instrument definition.
- ``conf.toml``: The configuration file with real instrument.
- ``conf_mock.toml``: The configuration file with mock instrument.

To launch the example:

- ``mahos launch``: with real instrument.
- ``mahos launch -c conf_mock.toml``: with mock instrument.
