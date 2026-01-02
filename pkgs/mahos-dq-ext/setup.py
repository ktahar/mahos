from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension

ext_modules = [
    Pybind11Extension(
        "mahos_dq_ext.cqdyne_analyzer",
        ["src/mahos_dq_ext/cqdyne_analyzer.cc"],
    ),
]

setup(ext_modules=ext_modules)
