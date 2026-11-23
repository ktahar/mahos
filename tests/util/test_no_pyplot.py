#!/usr/bin/env python3

"""
Tests that plotting modules used inside Nodes don't import matplotlib.pyplot.

pyplot selects a (possibly GUI) backend, and GUI figures garbage-collected on a
non-main thread can abort the Node process (e.g., Tcl_AsyncDelete with TkAgg).

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import subprocess
import sys

import pytest

CHECK_SCRIPT = """
import importlib
import pkgutil
import sys

import mahos.meas
import mahos_dq.meas

names = ["mahos.util.image", "mahos_dq.util.nv"]
for pkg in (mahos.meas, mahos_dq.meas):
    for info in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        if info.name.endswith("_io"):
            names.append(info.name)

for name in names:
    importlib.import_module(name)
    if "matplotlib.pyplot" in sys.modules:
        print(name)
        sys.exit(1)
print(len(names))
"""


@pytest.mark.timeout(60)
def test_io_modules_do_not_import_pyplot():
    # Run in a fresh interpreter because other tests may have imported pyplot already.
    proc = subprocess.run(
        [sys.executable, "-c", CHECK_SCRIPT], capture_output=True, text=True, timeout=60
    )
    assert proc.returncode == 0, (
        f"matplotlib.pyplot imported by: {proc.stdout.strip()}\n{proc.stderr}"
    )
    # Guard against silently checking nothing.
    assert int(proc.stdout.strip()) > 10
