# Licensed under a 3-clause BSD style license - see LICENSE.rst

# Packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._astropy_init import *   # noqa
# ----------------------------------------------------------------------------

# Enforce Python version check during package import.
# This is the same check as the one at the top of setup.py
import sys
from distutils.version import LooseVersion

__minimum_python_version__ = "3.7"

__all__ = []


class UnsupportedPythonError(Exception):
    pass


if LooseVersion(sys.version) < LooseVersion(__minimum_python_version__):
    raise UnsupportedPythonError("jdaviz does not support Python < {}"
                                 .format(__minimum_python_version__))

if not _ASTROPY_SETUP_:   # noqa
    # For egg_info test builds to pass, put package imports here.
    pass


from .config import tools
import ipyvuetify as v
from traitlets import Unicode


@tools('g-test-button')
class TestButton(v.VuetifyTemplate):
    template = Unicode("""
    <v-btn>Button</v-btn>
    """).tag(sync=True)

    def __init__(self, *args, hub=None, **kwargs):
        super().__init__(*args, **kwargs)
