Migration Guide
===============

Migrating from 0.3.x to 0.4.0
-----------------------------

MAHOS 0.4.0 contains several user-visible changes. This page summarizes the changes
that may require updates in existing environments, configuration files, and user scripts.

Python version
^^^^^^^^^^^^^^

MAHOS 0.4.0 requires Python 3.11 or later. Python 3.10 is no longer supported.

Create a new virtual environment with a supported Python version before upgrading:

.. code-block:: bash

   python3.11 -m venv mahos
   source mahos/bin/activate

See :doc:`installation` for the current installation procedure.

Package split
^^^^^^^^^^^^^

Application-specific modules for defect spin qubit experiments have been moved from
``mahos`` to the new ``mahos_dq`` package. The optional C extensions live in ``mahos_dq_ext``.

If your configuration files refer to modules such as ``mahos.meas.odmr`` or
``mahos.gui.confocal``, update those module paths to ``mahos_dq``:

.. code-block:: toml

   # 0.3.x
   module = "mahos.meas.odmr"

   # 0.4.0
   module = "mahos_dq.meas.odmr"

The following Python script handles the common configuration-file replacements.
Save it as ``migrate_mahos_0_4.py``, run it from the directory that contains
your TOML configuration files, then review the diff carefully before using the migrated files.

.. code-block:: python

   #!/usr/bin/env python3

   import re
   import shutil
   import sys
   from pathlib import Path

   DQ_MODULES = "confocal|hbt|spectroscopy|qdyne|odmr|podmr|spodmr|iodmr"
   OVERLAY_MODULES = "odmr_sweeper|iodmr_sweeper|confocal_scanner"

   def migrate_text(text):
       text = re.sub(
           rf'\bmahos\.(meas|gui|msgs)\.({DQ_MODULES})(?=[._"])',
           r"mahos_dq.\1.\2",
           text,
       )
       text = re.sub(
           rf'\bmahos\.inst\.overlay\.({OVERLAY_MODULES})(?=[._"])',
           r"mahos_dq.inst.overlay.\1",
           text,
       )
       # Old examples sometimes used bare module names for these overlays.
       return re.sub(
           rf"""(module\s*=\s*(['"]))({OVERLAY_MODULES})(?=[\w.]*\2)""",
           r"\1mahos_dq.inst.overlay.\3",
           text,
       )

   def migrate_file(path):
       old = path.read_text()
       new = migrate_text(old)
       if new == old:
           return False

       backup = Path(str(path) + ".bak")
       if not backup.exists():
           shutil.copy2(path, backup)
       path.write_text(new)
       return True

   def main():
       root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
       changed = [path for path in sorted(root.rglob("*.toml")) if migrate_file(path)]
       for path in changed:
           print(path)
       print(f"migrated {len(changed)} file(s)")

   if __name__ == "__main__":
       main()

This script creates ``*.toml.bak`` files before modifying each TOML file.
After running the script, inspect the changed paths and search for remaining old module references:

.. code-block:: bash

   git diff
   grep -RE "mahos\.(meas|gui|msgs)\.(confocal|hbt|spectroscopy|qdyne|odmr|podmr|spodmr|iodmr)" .

TOML parser strictness
^^^^^^^^^^^^^^^^^^^^^^

MAHOS now uses Python's standard-library ``tomllib`` module to load configuration files.
``tomllib`` implements TOML 1.0 more strictly than the previous ``toml`` package.

One important difference is that an inline table cannot be extended later.
This form may have been accepted by the old parser, but it is invalid TOML 1.0:

.. code-block:: toml

   [localhost.tweaker]
   module = "mahos.meas.tweaker"
   class = "Tweaker"
   target = { log = "localhost::log" }
   rep_endpoint = "tcp://127.0.0.1:5561"
   pub_endpoint = "tcp://127.0.0.1:5562"

   [localhost.tweaker.target.servers]
   source = "localhost::server"

Write ``target`` as a normal table if you need to add nested keys:

.. code-block:: toml

   [localhost.tweaker]
   module = "mahos.meas.tweaker"
   class = "Tweaker"
   rep_endpoint = "tcp://127.0.0.1:5561"
   pub_endpoint = "tcp://127.0.0.1:5562"

   [localhost.tweaker.target]
   log = "localhost::log"

   [localhost.tweaker.target.servers]
   source = "localhost::server"

Inline tables are still fine when all keys are defined inside the braces and
no nested table is added later:

.. code-block:: toml

   [localhost.log]
   module = "mahos.node.log_broker"
   class = "LogBroker"
   target = { log = "localhost::log" }

Installation commands
^^^^^^^^^^^^^^^^^^^^^

Development dependencies are now provided through the ``dev`` extra of the base package.
For a development checkout, use:

.. code-block:: bash

   pip install -e "./pkgs/mahos[dev]" -e ./pkgs/mahos-dq

Install the optional C extension package only when needed:

.. code-block:: bash

   pip install -e ./pkgs/mahos-dq-ext

Migration checklist
^^^^^^^^^^^^^^^^^^^

- Recreate your environment with Python 3.11 or later.
- Install ``mahos`` and ``mahos_dq`` according to :doc:`installation`.
- Update ``mahos.meas.*``, ``mahos.gui.*``, and ``mahos.msgs.*`` references
  for the modules moved to ``mahos_dq``.
- Fix any TOML inline tables that are extended by later table declarations.
- Launch your system with the migrated configuration file and check import errors first;
  they usually identify remaining stale module paths.
