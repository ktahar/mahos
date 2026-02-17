Architecture
============

As introduced in :doc:`overview`, the mahos system consists of nodes that are categorized into three layers, as visualized below.

.. toctree::
   :maxdepth: 1

   arch_node
   arch_inst
   arch_meas
   arch_gui

.. figure:: ./img/mahos-layers.svg
   :alt: Overview of nodes in the layers
   :width: 80%

   Overview of nodes in the layers

Package layout
--------------

Currently, mahos contains two main subpackages.

mahos
^^^^^

The mahos package has core functionality of the mahos system and common components.

* :ref:`mahos.node` - Base node implementations.
* :ref:`mahos.msgs` - Message type definitions.
* :ref:`mahos.inst` - Low-level drivers for instruments. :class:`InstrumentServer <mahos.inst.server.InstrumentServer>` node provides RPC with unified API.
* :ref:`mahos.meas` - High-level measurement logics. (explicit state management and file I/O, etc.).
* :ref:`mahos.gui` - GUI frontends.
* :ref:`mahos.cli <mahos.cli>` - Command Line Interfaces.

mahos_dq
^^^^^^^^

The mahos_dq package has logic and GUI for solid-state Defect (color center) Qubit research.
The submodule layout is similar to that of mahos.

* :ref:`mahos_dq.msgs` - Message type definitions.
* :ref:`mahos_dq.inst` - :class:`InstrumentOverlay <mahos.inst.overlay.overlay.InstrumentOverlay>` definitions.
* :ref:`mahos_dq.meas` - High-level measurement logics.
* :ref:`mahos_dq.gui` - GUI frontends.
