Data transport in BasicMeasNode
===============================

BasicMeasNode implements efficient transport mechanisms for both live and buffer data.

Incremental live data transport
-------------------------------

BasicMeasNode can optionally distribute growing arrays in live data as incremental updates.
Enable this in the measurement node's configuration::

    [localhost.odmr]
    # Other node settings, including pub_endpoint, remain necessary.
    data_transport = "incremental"
    sync_endpoint = "tcp://127.0.0.1:5563"

``data_transport`` defaults to ``"pubsub"``, which preserves conventional full-object publication.
``sync_endpoint`` is required in incremental mode and must be a distinct, client-accessible endpoint.

Among the built-in BasicMeasNodes, ODMR, APODMR, and SPODMR support incremental transport.
ODMR sends ``data`` and ``bg_data`` along axis 1, retransmitting the last column because it may still be filled in place.
SPODMR sends complete appended columns of ``data0`` and ``data1`` along axis 1, without a mutable tail.
APODMR sends ``raw_data`` along axis 0 using its cumulative ``records`` counter.
With ``max_records = 0``, records append indefinitely;
with a positive limit, updates discard expired rows and append new records.
If no records overlap the previous publication, the retained array is replaced in full.
Its ``signal_history`` and ``reference_history`` append along axis 0 while enabled and remain ``None`` while disabled.
History rebuilds after analysis-window changes force replacement.

Confocal and TraceNode also support these settings for their ``trace`` topic.
Both ``Trace.traces`` and ``Trace.stamps`` remain lists of per-channel arrays.
Channels start empty and grow independently up to ``max_size``, then retain the latest samples.
``sample_counts`` counts received samples since clear, including samples that have rolled out.
Clearing a trace increments ``generation`` to invalidate retained overlap.
Oversized input batches retain the latest samples. Pause/resume preserves the existing frozen
trace behavior; switching between frozen and live objects starts a new transport epoch.

Python and Qt measurement clients reconstruct the ordinary data classes before invoking handlers or emitting signals.
Each delivered object contains one complete revision, including metadata and all selected arrays.

Implementing incremental transport
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To support another ``BasicMeasNode`` subclass, define ``INCREMENTAL_ARRAYS`` as a mapping
from attribute names to ``mahos.node.data_transport.ArrayPolicy(axis, mutable_tail)``.
Selected attributes must be NumPy arrays with non-object dtype, or ``None``.
The optional ``count_attr`` policy field names a cumulative slice counter for a rolling array;
the array must contain the latest slices ending at that count.
With ``sequence=True``, the attribute is a list of arrays, and ``count_attr`` names a list of corresponding counters.
Each element is reconstructed independently; a channel-count change replaces the list.
The generation token applies to the whole list.
This rolling array mode cannot be combined with a mutable tail.
The optional ``generation_attr`` names a scalar generation token whose change forces array replacement.
For example, APODMR increments ``history_generation`` whenever history is cleared, including rebuilds between publications.
Existing ``self.data_pub.publish(data)`` calls remain unchanged.
Previously published elements outside the mutable tail must remain unchanged unless replacement is forced.
Metadata and arrays must be coherent while ``publish()`` runs, as with conventional serialization.
Replacing the data object starts a new generation; uncounted array shrinkage, dtype changes,
and changes to other dimensions cause full array replacement.
When an in-place edit to historical elements cannot be avoided,
call ``self.data_pub.invalidate()`` before the next publication.

Versioned buffer transport
--------------------------

Buffer transport is selected independently of live-data transport::

    [localhost.podmr]
    buffer_transport = "versioned"
    sync_endpoint = "tcp://127.0.0.1:5563"

``buffer_transport`` defaults to ``"pubsub"``.
Versioned mode is supported by ODMR, PODMR, APODMR, SPODMR, HBT, and Spectroscopy.
A client-accessible ``sync_endpoint`` is required when either versioned buffers or incremental live data
are enabled; the two transports share one recovery service and endpoint when enabled together.

Versioned mode periodically publishes a small ordered manifest on ``versioned_buffer``
instead of sending full objects on ``buffer``.

Python and Qt clients fetch missing exact entry versions asynchronously and reconstruct
ordinary :class:`mahos.msgs.common_meas_msgs.Buffer` objects in manifest order.
Getters, callback signatures, Qt signals, and dataset types are unchanged.
Repeated identical manifests cause neither downloads nor repeated callbacks.
Appending an entry downloads only the new entry; marking an existing entry changed downloads that complete entry again.
Clients retain their last complete buffer until every entry in the replacement is available.

Implementing buffered measurements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Initialize node-owned storage with ``self.buffer = self.new_buffer()`` after
``BasicMeasNode.__init__()``. This selects ordinary storage in conventional mode or a
:class:`mahos.msgs.common_meas_msgs.TrackedBuffer` in versioned mode.
Existing ``self.buffer_pub.publish(self.buffer)`` calls remain unchanged and must continue periodically even while idle.

Use the buffer's list operations for structural edits, including append, pop, clear,
slice replacement, reverse, and sort. Do not modify its underlying ``.data`` list directly.
After modifying any retrieved dataset or its metadata, call ``self.buffer.touch(index)``.
Every affected entry must be marked, including entries sharing a modified object reference.
``touch()`` is a no-op for ordinary buffers. Transport identities and revisions are kept
in node-owned storage, outside persisted measurement data and delivered buffer objects.

Keep batch mutations on the node thread, mark all affected entries, then publish.
Use ``finally`` where an operation can partially modify data before raising:
an error must not leave changed data associated with its old revision.
Common fitting and fit clearing operations, as well as PODMR/APODMR/SPODMR/HBT plot updates, follow this contract.
Plot-update marking is conservative because these operations can modify metadata even when no new analysis result is reported.

Changes become available to clients at the next publication.
Clients may skip intermediate buffer revisions; versioned transport does not provide a history of changes.
Copying and serialization still have a cost: reanalysis of every entry requires downloading every entry again.
