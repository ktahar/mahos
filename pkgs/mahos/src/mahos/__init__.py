#!/usr/bin/env python3

"""
The mahos package

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import os

# resolved lazily via __getattr__()
__version__: str

__all__ = [
    "cli",
    "gui",
    "inst",
    "meas",
    "msgs",
    "node",
    "util",
    "load_gconf",
    "local_conf",
    "__version__",
]

HOME_DIR = os.environ.get("MAHOS_HOME", os.path.expanduser(os.path.join("~", ".mahos")))
CONFIG_DIR = os.path.join(HOME_DIR, "config")
LOG_DIR = os.path.join(HOME_DIR, "log")

for d in (CONFIG_DIR, LOG_DIR):
    if not os.path.exists(d):
        os.makedirs(d)
        print("Directory {} is created.".format(d))


def __getattr__(name: str):
    if name in ("load_gconf", "local_conf"):
        from mahos.node.node import load_gconf as _load_gconf, local_conf as _local_conf

        globals()["load_gconf"] = _load_gconf
        globals()["local_conf"] = _local_conf
        return globals()[name]
    if name == "__version__":
        from mahos.version import get_mahos_version

        v = get_mahos_version()
        globals()["__version__"] = v
        return v
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
