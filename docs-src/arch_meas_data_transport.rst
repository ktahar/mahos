Data transport in BasicMeasNode
===============================

Incremental live data transport
-------------------------------

BasicMeasNode can optionally distribute growing arrays in live data as incremental updates.
Enable this in the measurement node's configuration (use the same configuration for its clients)::

    [localhost.odmr]
    # Other node settings, including pub_endpoint, remain necessary.
    data_transport = "incremental"
    sync_endpoint = "tcp://127.0.0.1:5563"

``data_transport`` defaults to ``"pubsub"``, which preserves conventional full-object publication.
``sync_endpoint`` is required in incremental mode and must be a distinct, client-accessible endpoint.

Among the builtin BasicMeasNodes, ODMR, APODMR, and SPODMR support the incremental transport now.
Unsupported measurements reject incremental mode at startup.
Array policies must be defined by the node implementation.
ODMR sends ``data`` and ``bg_data`` along axis 1, retransmitting the last column because it may still
be filled in place.
SPODMR sends complete appended columns of ``data0`` and ``data1`` along axis 1, without a mutable tail.
APODMR sends ``raw_data`` along axis 0 using its cumulative ``records`` counter.
With ``max_records = 0``, records append indefinitely;
with a positive limit, updates discard expired rows and append new records.
If no records overlap the previous publication, the retained array is replaced in full.
Its ``signal_history`` and ``reference_history`` append along axis 0 while enabled and remain
``None`` while disabled. History rebuilds after analysis-window changes force replacement,
even when the array shape is unchanged.

Python and Qt measurement clients reconstruct the ordinary data classes before invoking handlers or emitting signals.
Each delivered object contains one complete revision, including metadata and all selected arrays.
Previously delivered objects remain stable.

The node retains its last published state. A dedicated thread owns the ROUTER recovery
socket and serves that state even while the measurement thread is waiting for an instrument.
Publication replaces one immutable state reference under a short lock; serialization and
network operations run outside the lock. The service serializes a revision only when a
snapshot is requested, and caches the most recently serialized revision for reuse across
clients. Recovery responses contain a small header and an optional separate snapshot frame.
Snapshot payloads always use pickle with the project's pickle protocol version, bypassing
custom ``Message.serialize()`` and ``Message.deserialize()`` methods, consistently with the
incremental envelopes.
Queued duplicate requests from the same client are coalesced within bounded batches;
later retries still receive responses. No historical snapshot queue is maintained.
Shutdown joins the service before closing the ZMQ context and waits for any serialization
already in progress to finish.

This removes recovery serialization from the measurement thread, but does not eliminate
CPU or memory-bandwidth contention. Publication and client reconstruction still copy arrays.
The snapshot service exposes only committed publications, not unpublished worker mutations.
Clients request a snapshot on startup and after a missing revision,
and check the latest revision about once per second even while acquisition is idle.
Unanswered requests are retried after five seconds using the same request ID and arguments,
so responses remain valid when acquisition or transfer takes longer. Duplicate responses
are ignored once the logical request completes.
Recovery is asynchronous and does not use the client's ordinary measurement request socket.
No unbounded update history or startup buffer is retained.
Clients converge to the last published revision when communication succeeds;
publication itself does not wait for acknowledgements from every client.
Clients may skip intermediate revisions during recovery.
A disconnected client retains its last complete data object.
Malformed requests are logged and rejected without interrupting acquisition. Clients log
invalid updates or recovery responses, retain their last complete replica, and request
recovery. Incompatible protocol versions produce explicit diagnostics. Exceptions raised
by application data handlers are not treated as transport failures.

Transport threads enqueue diagnostics rather than calling socket-backed logging handlers.
The node thread forwards snapshot-service records through its normal logger during polling
and shutdown, before the logging handler is detached. Diagnostics can therefore be delayed
while acquisition blocks. Python clients forward subscription diagnostics through their
client logger when the owning thread reads a subscription getter, polls an owning node, or
closes the client. Qt clients drain their queue on a main-thread timer to their console logger.
Each queue holds up to 1024 records; overflow is counted and reported on the next drain.
Original log timestamps, source locations, and formatted exception text are preserved.
Client shutdown stops accepting new records and completes a final owning-thread drain.
Parent contexts borrow client log queues and unregister closed, drained queues during their
own polling; clients do not modify the parent's polling registrations. Closing a parent
releases its registrations without closing queues belonging to still-live clients.

To support another ``BasicMeasNode`` subclass, define ``INCREMENTAL_ARRAYS`` as a mapping
from attribute names to ``mahos.node.data_transport.ArrayPolicy(axis, mutable_tail)``.
The optional ``count_attr`` policy field names a cumulative slice counter for a rolling array;
the array must contain the latest slices ending at that count.
This mode cannot be combined with a mutable tail.
The optional ``generation_attr`` names a scalar generation token whose change forces array replacement.
APODMR increments ``history_generation`` whenever history is cleared, including rebuilds between publications.
The existing ``self.data_pub.publish(data)`` calls remain unchanged. Selected attributes
must be NumPy arrays without object dtype, or ``None``. Previously published elements
outside the mutable tail must not change.
Replacing the data object starts a new generation; uncounted array shrinkage, dtype changes,
and changes to other dimensions cause full array replacement.
For an in-place edit to historical elements, call ``self.data_pub.invalidate()`` before the
next publication when incremental mode is active. Metadata and arrays must be coherent
while ``publish()`` runs, as with conventional serialization.
