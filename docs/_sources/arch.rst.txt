Architecture
============

As introduced in :doc:`overview`, mahos system consists of nodes which are categorized into three layers as visualized below.

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

mahos package has core functionalities of mahos's system and common components.

* :ref:`mahos.node` - Base node implementations.
* :ref:`mahos.msgs` - Message type definitions.
* :ref:`mahos.inst` - Low-level drivers for instruments. :class:`InstrumentServer <mahos.inst.server.InstrumentServer>` node provides RPC with unified API.
* :ref:`mahos.meas` - High-level measurement logics. (explicit state management and file I/O, etc.).
* :ref:`mahos.gui` - GUI frontends.
* :ref:`mahos.cli <mahos.cli>` - Command Line Interfaces.

mahos_dq
^^^^^^^^

mahos_dq package has logics and gui for solid-state Defect (color center) Qubits research.
The layout of submodule is similar to mahos.

* :ref:`mahos_dq.msgs` - Message type definitions.
* :ref:`mahos_dq.inst` - :class:`InstrumentOverlay <mahos.inst.overlay.overlay.InstrumentOverlay>` definitions.
* :ref:`mahos_dq.meas` - High-level measurement logics.
* :ref:`mahos_dq.gui` - GUI frontends.
