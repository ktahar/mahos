#####
MAHOS
#####

|build_badge| |paper_badge|

.. |build_badge| image:: https://github.com/ktahar/mahos/actions/workflows/build.yaml/badge.svg

.. |paper_badge| image:: https://joss.theoj.org/papers/10.21105/joss.05938/status.svg
   :target: https://doi.org/10.21105/joss.05938

MAHOS: Measurement Automation Handling and Orchestration System.

This repository currently includes the following packages.

- ``mahos``: Base system for distributed measurement automation.
- ``mahos-dq``: Implementations of microscopy / optically detected magnetic resonance (ODMR) system
  for solid-state defect (color center) spin qubit research, based on ``mahos``.
- ``mahos-dq-ext``: C++ extension module for ``mahos-dq``.

Documentation
=============

`Documentation is browsable here <https://ktahar.github.io/mahos/>`_.

You can also browse the documentation locally by ``make browse`` or
opening ``docs`` directory with a web browser.

Install
=======

Read the `Installation guide <https://ktahar.github.io/mahos/installation.html>`_.

In short, we recommend editable installation with cloned repository:

#. Clone this repo somewhere.
#. Install the ``mahos`` package: ``pip install -e ./pkgs/mahos`` or ``pip install -e ./pkgs/mahos[inst]``
   (the latter installs optional packages for instrument drivers).
#. (optional) Install the ``mahos-dq`` and ``mahos-dq-ext`` packages: ``pip install -e ./pkgs/mahos-dq`` and ``pip install -e ./pkgs/mahos-dq-ext``.
#. Test the installation with ``pytest``.

Run
===

To use the mahos-based system, you need to write a toml `configuration file <https://ktahar.github.io/mahos/conf.html>`_ first.
With your config, use the `command line interface <https://ktahar.github.io/mahos/cli.html>`_ to start the nodes and interact with them.

- The `tutorial <https://ktahar.github.io/mahos/tutorial.html>`_ and corresponding `examples <https://github.com/ktahar/mahos/tree/main/examples>`_ are provided to get used to these concepts.
- `Realistic examples <https://github.com/ktahar/mahos/tree/main/examples/cfm>`_ are provided for confocal microscope / ODMR system using ``mahos-dq``.
- There is an `example config <https://github.com/ktahar/mahos/blob/main/tests/conf.toml>`_ for the unit test too.
  Here you can observe main built-in measurement logics and GUIs with mock instruments.

Cite
====

If you publish a research work based on MAHOS, we would be grateful if you could cite `this paper <https://doi.org/10.21105/joss.05938>`_ . The BibTeX snippet can be copied below.

.. code-block:: bibtex

  @article{Tahara2023, doi = {10.21105/joss.05938}, url = {https://doi.org/10.21105/joss.05938}, year = {2023}, publisher = {The Open Journal}, volume = {8}, number = {91}, pages = {5938}, author = {Kosuke Tahara}, title = {MAHOS: Measurement Automation Handling and Orchestration System}, journal = {Journal of Open Source Software} }

License
=======

The mahos project is licensed under the `3-Clause BSD License <https://github.com/ktahar/mahos/blob/main/LICENSE>`_.

Redistribution
--------------

The `GUI theme <https://github.com/ktahar/mahos/tree/main/pkgs/mahos/src/mahos/gui/breeze_resources>`_ is taken from `BreezeStyleSheets <https://github.com/Alexhuszagh/BreezeStyleSheets>`_ project,
which is licensed under the `MIT license: Copyright 2013-2014 Colin Duquesnoy and 2015-2016 Alex Huszagh <https://github.com/Alexhuszagh/BreezeStyleSheets/blob/main/LICENSE.md>`_.

A `file <https://github.com/ktahar/mahos/blob/main/pkgs/mahos/src/mahos/util/unit.py>`_ includes a function from the `pyqtgraph <https://github.com/pyqtgraph/pyqtgraph>`_ project,
which is licensed under the `MIT license: Copyright 2012 Luke Campagnola, University of North Carolina at Chapel Hill <https://github.com/pyqtgraph/pyqtgraph/blob/master/LICENSE.txt>`_.

Contributing
============

Please check out `Contribution Guidelines <https://ktahar.github.io/mahos/contributing.html>`_.
