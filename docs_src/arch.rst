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

mahos.core
^^^^^^^^^^

mahos.core implements core functionalities of mahos's system and common components.

* :ref:`mahos.core.node` - Base node implementations.
* :ref:`mahos.core.msgs` - Message type definitions.
* :ref:`mahos.core.inst` - Low-level drivers for instruments. :class:`InstrumentServer <mahos.core.inst.server.InstrumentServer>` node provides RPC with unified API.
* :ref:`mahos.core.meas` - High-level measurement logics. (explicit state management and file I/O, etc.).
* :ref:`mahos.core.gui` - GUI frontends.
* :ref:`mahos.core.cli <mahos.core.cli>` - Command Line Interfaces.

mahos.dq
^^^^^^^^

mahos.dq implements logics and gui for solid-state Defect (color center) Qubits research.
The layout of submodule is similar to mahos.core.

* :ref:`mahos.dq.msgs` - Message type definitions.
* :ref:`mahos.dq.inst` - :class:`InstrumentOverlay <mahos.core.inst.overlay.InstrumentOverlay>` definitions.
* :ref:`mahos.dq.meas` - High-level measurement logics.
* :ref:`mahos.dq.gui` - GUI frontends.
