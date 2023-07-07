# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

from astropy.tests.runner import TestRunner

try:
    from .version import version as __version__
except ImportError:
    __version__ = ''

# Create the test function for self test
test = TestRunner.make_test_runner_in(os.path.dirname(__file__))

# Top-level API as exposed to users.
from jdaviz.app import *  # noqa: F401, F403
from jdaviz.configs.specviz import Specviz  # noqa: F401
from jdaviz.configs.specviz2d import Specviz2d  # noqa: F401
from jdaviz.configs.mosviz import Mosviz  # noqa: F401
from jdaviz.configs.cubeviz import Cubeviz  # noqa: F401
from jdaviz.configs.imviz import Imviz  # noqa: F401
from jdaviz.utils import enable_hot_reloading  # noqa: F401
from jdaviz.core.launcher import open  # noqa: F401

# Clean up namespace.
del os
del TestRunner
