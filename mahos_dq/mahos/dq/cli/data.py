#!/usr/bin/env python3

from mahos.dq.msgs.confocal_msgs import Image, Trace
from mahos.dq.msgs.odmr_msgs import ODMRData
from mahos.dq.msgs.podmr_msgs import PODMRData
from mahos.dq.msgs.spodmr_msgs import SPODMRData
from mahos.dq.msgs.iodmr_msgs import IODMRData
from mahos.dq.msgs.hbt_msgs import HBTData
from mahos.dq.msgs.spectroscopy_msgs import SpectroscopyData

exts_to_data = {
    ".scan.h5": Image,
    ".trace.h5": Trace,
    ".odmr.h5": ODMRData,
    ".podmr.h5": PODMRData,
    ".spodmr.h5": SPODMRData,
    ".iodmr.h5": IODMRData,
    ".hbt.h5": HBTData,
    ".spec.h5": SpectroscopyData,
}
