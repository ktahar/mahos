Configuration tips
==================

This page is a collection of configuration tips.

Selecting analog PD inputs
--------------------------

``AnalogIn`` (including ``AnalogPD``) and ``Spectrum_AnalogIn`` accept a runtime
``channel_selection`` list. Entries are zero-based indices into the instrument's
configured ``lines``, not physical channel numbers. The list must be nonempty and
strictly increasing. Only selected inputs are enabled in hardware; omitting the
parameter or passing ``None`` restores all configured inputs. Per-channel bounds
and static input settings always use the full ``lines`` order.

Measurement workers supply this parameter through static ``pd_channel_selection``
configuration. For example, a Spectrum instrument with ``lines = [0, 2, 4, 6]`` can
be shared by a TraceNode reading all four inputs and APODMR reading physical input 4::

    # TraceNode tracer configuration
    pd_names = ["pd0"]
    pd_channels = [4]

    # APODMR pulser configuration
    pd_names = ["pd0"]
    pd_channel_selection = { pd0 = [2] }

Use the same mapping under SPODMR's ``pulser`` or ODMR's direct ``sweeper``
configuration. For overlay-based ODMR, place it in the overlay instrument's
configuration. Missing PD entries acquire all inputs. Trace derives the expected
output count from an explicit selection only when ``pd_channels`` is omitted.
An explicit ``pd_channels`` is authoritative. Inference assumes one output per
physical input; instruments that combine inputs require explicit logical counts.
For example, use ``pd_channels = [1]`` with
``pd_channel_selection = { pd0 = [0, 1] }`` for a ``LockinAnalogPD``.
Selection is static and requires restarting the node to change.

Counters do not support this option. ``LockinAnalogPD`` requires both physical
X/Y inputs and continues to return one complex output. Hardware restrictions on
valid channel combinations still apply. Actual sampling-rate improvements depend
on the acquisition hardware.
