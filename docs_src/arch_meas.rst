meas layer
==========

The meas layer is implementated as :ref:`mahos.meas` package.
The nodes in the meas layer provides the core functionalities of the measurement automation.
To keep flexibility, there is almost no restriction on node implementation.

However, meas nodes are advised to have explicit :term:`state`, i.e., to publish topic :term:`status` (:class:`Status <mahos.msgs.common_msgs.Status>` type) having :term:`state` attribute (:class:`State <mahos.msgs.common_msgs.State>` type).
If the node has :term:`state`, we can use `StateManager`_ for the state management.

BasicMeasNode
-------------

:class:`BasicMeasNode <mahos.meas.common_meas.BasicMeasNode>` can be utilized as a base class to implement basic measurment nodes.
This class assumes :term:`state` of type :class:`BinaryState <mahos.msgs.common_msgs.BinaryState>` and :term:`status` of type :class:`BinaryStatus <mahos.msgs.common_msgs.BinaryStatus>`.

.. _meas-tweaker:

Tweaker
-------

:class:`Tweaker <mahos.meas.tweaker.Tweaker>` is a generic node for manual-tuning of instrument parameters.
This is useful for rather "floating" instruments which is not directly tied to specific measurement protocol,
but its state affects the sample / DUT and measurement result.
Examples: programmable (variable gain) amplifiers for the sensors, thermostats, or power supply for electromagnet.
The instrument should have :ref:`inst-params-interface` to be managed by the Tweaker.

Recorder
--------

:class:`Recorder <mahos.meas.recorder.Recorder>` is a generic node for recording of time-series data from instruments.
The instrument should provide several interfaces to be used by the Recorder.

StateManager
------------

:class:`StateManager <mahos.meas.state_manager.StateManager>` is used as a manager of meas node states.
It subscribes to topic :term:`states <state>` of all the managed nodes.
We can register the `command` for the manager, which is a map from nodes to required states.
Example configuration looks like below.

.. code-block:: toml

   [localhost.manager1.node]
   "localhost::node1" = ["mahos.msgs.common_msgs", "BinaryState"]
   "localhost::node2" = ["mahos.msgs.common_msgs", "BinaryState"]

   [localhost.manager1.command]
   all_idle = { "localhost::node1" = "IDLE" , "localhost::node2" = "IDLE" }

This manager manages `node1` and `node2`, both of which has :class:`BinaryState <mahos.msgs.common_msgs.BinaryState>`.
A command named `all_idle` is a request to set both nodes to the IDLE state.
Before a `command` is executed, the nodes state (`last_state`) is stored.
After a `command`, we can use `restore` request to recover the `last_state`.

The figure below explans the `command` and `restore` operations.

.. figure:: ./img/mahos-state-manager.svg
   :alt: Command and Restore operations of StateManager
   :width: 90%

   Command and Restore operations of StateManager

The manager1 is configured as the config snippets above.

* (a): In initial state, node1 is ACTIVE and node2 is IDLE.
* (b): node3 requests the manager1 to `restore` from `all_idle` command (Restore(all_idle)), which fails as the `last_state` is empty (`all_idle` has never been executed).
* (c): node3 requests `all_idle` command execution (Command(all_idle), which turns both node1 and node2 to IDLE states. Here, the `last_state` is stored.
* (d): node3 requests (Restore(all_idle) again. It succeeds this time and `last_state` is restored (node1 becomes ACTIVE).
