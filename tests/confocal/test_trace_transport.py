"""Incremental transport tests for confocal trace buffers."""

import numpy as np
import pytest

import mahos.node.data_transport as transport_module
from mahos.node.data_transport import ArrayPolicy, IncrementalPublisher, IncrementalSubscriber
from shared.transport import pump


@pytest.mark.parametrize("complex_data", [False, True])
def test_trace_lists_rolling_and_reset(transport, complex_data):
    from mahos_dq.msgs.confocal_msgs import Trace
    from mahos_dq.meas.confocal_worker import Tracer

    server, client, conf = transport
    pub = IncrementalPublisher(
        server,
        conf["pub_endpoint"],
        conf["sync_endpoint"],
        {
            name: ArrayPolicy(
                0, count_attr="sample_counts", generation_attr="generation", sequence=True
            )
            for name in ("traces", "stamps")
        },
    )
    received = []
    transport_module.add_data_subscription(client, conf, b"trace", received.append)
    worker = Tracer.__new__(Tracer)
    worker.size = 8
    worker.trace = Trace(8, 2, complex_data)
    pub.publish(worker.trace)
    pump(server, client, lambda: bool(received))
    original = received[-1]
    for ch, count in [(0, 3), (1, 2), (0, 19)]:
        values = np.arange(count, dtype=float) + 1
        if complex_data:
            values = values + 2j
        worker._append_trace_data(ch, values, np.arange(1, count + 1).astype("datetime64[ns]"))
        op = pub._extract(worker.trace, False, "traces", pub.policies["traces"], ch)
        assert len(op[3]) == min(count, 8)
        pub.publish(worker.trace)
        expected = worker.trace.sample_counts.copy()
        pump(server, client, lambda: received[-1].sample_counts == expected)
        for name in ("traces", "stamps"):
            assert isinstance(getattr(received[-1], name), list)
            np.testing.assert_equal(getattr(received[-1], name), getattr(worker.trace, name))
    assert original.sample_counts == [0, 0]
    assert not np.any(original.traces)
    worker.trace.clear()
    worker._append_trace_data(0, np.ones(22), np.arange(22).astype("datetime64[ns]"))
    pub.publish(worker.trace)
    pump(server, client, lambda: received[-1].generation == 1)
    np.testing.assert_equal(received[-1].traces, worker.trace.traces)
    # Late subscribers recover the entire list-valued snapshot.
    late = []
    IncrementalSubscriber(client, conf, late.append)
    pump(server, client, lambda: bool(late))
    np.testing.assert_equal(late[-1].stamps, worker.trace.stamps)
