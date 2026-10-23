Data transport in BasicMeasNode
===============================

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

Among the builtin BasicMeasNodes, ODMR, APODMR, and SPODMR support the incremental transport now.
ODMR sends ``data`` and ``bg_data`` along axis 1, retransmitting the last column because it may still be filled in place.
SPODMR sends complete appended columns of ``data0`` and ``data1`` along axis 1, without a mutable tail.
APODMR sends ``raw_data`` along axis 0 using its cumulative ``records`` counter.
With ``max_records = 0``, records append indefinitely;
with a positive limit, updates discard expired rows and append new records.
If no records overlap the previous publication, the retained array is replaced in full.
Its ``signal_history`` and ``reference_history`` append along axis 0 while enabled and remain ``None`` while disabled.
History rebuilds after analysis-window changes force replacement.

Python and Qt measurement clients reconstruct the ordinary data classes before invoking handlers or emitting signals.
Each delivered object contains one complete revision, including metadata and all selected arrays.

To support another ``BasicMeasNode`` subclass, define ``INCREMENTAL_ARRAYS`` as a mapping
from attribute names to ``mahos.node.data_transport.ArrayPolicy(axis, mutable_tail)``.
Selected attributes must be NumPy arrays with non-object dtype, or ``None``.
The optional ``count_attr`` policy field names a cumulative slice counter for a rolling array;
the array must contain the latest slices ending at that count.
This rolling array mode cannot be combined with a mutable tail.
The optional ``generation_attr`` names a scalar generation token whose change forces array replacement.
For example, APODMR increments ``history_generation`` whenever history is cleared, including rebuilds between publications.
The existing ``self.data_pub.publish(data)`` calls remain unchanged, but care must be taken on mutable operations on the data.
Previously published elements outside the mutable tail must not change (that breaks basic assumption of this transport mechanism).
Metadata and arrays must be coherent while ``publish()`` runs, as with conventional serialization.
Replacing the data object starts a new generation; uncounted array shrinkage, dtype changes,
and changes to other dimensions cause full array replacement (though these should not happen in normal operation).
When an in-place edit to historical elements cannot be avoided,
call ``self.data_pub.invalidate()`` before the next publication.
