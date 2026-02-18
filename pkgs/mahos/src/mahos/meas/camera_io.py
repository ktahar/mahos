#!/usr/bin/env python3

"""
File I/O for Camera.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
from os import path

# import numpy as np
import matplotlib.pyplot as plt

from mahos.msgs.camera_msgs import Image
from mahos.node.log import DummyLogger
from mahos.util.io import save_pickle_or_h5, load_pickle_or_h5


class CameraIO(object):
    """IO class for Camera."""

    def __init__(self, logger=None):
        if logger is None:  # use DummyLogger on interactive use
            self.logger = DummyLogger(self.__class__.__name__)
        else:
            self.logger = logger

    def save_data(self, file_name: str, image: Image, note: str = "") -> bool:
        """Save data to file_name. return True on success."""

        return save_pickle_or_h5(file_name, image, Image, self.logger, note=note)

    def load_data(self, file_name: str) -> Image | None:
        """Load data from file_name. return None if load is failed."""

        return load_pickle_or_h5(file_name, Image, self.logger)

    def export_data(self, file_name: str, image: Image, params: dict | None = None) -> bool:
        """Export the data to text or image files.

        :param file_name: supported extensions: .png, .pdf, and .eps.

        """

        if params is None:
            params = {}

        if not isinstance(image, Image):
            self.logger.error(f"Given object ({image}) is not an Image.")
            return False

        ext = path.splitext(file_name)[1]
        if ext in (".png", ".pdf", ".eps"):
            return self._export_data_image(file_name, image, params)
        else:
            self.logger.error(f"Unknown extension to export image: {file_name}")
            return False

    def _export_data_image(self, file_name: str, image: Image, params):
        fig = plt.figure()
        fig.add_subplot(111)

        plt.imshow(image.image, origin="upper")

        plt.savefig(file_name)
        plt.close()

        self.logger.info(f"Exported Image to {file_name}.")
        return True
