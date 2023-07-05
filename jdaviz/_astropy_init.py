# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
import sys

if not hasattr(sys.modules["__main__"], "__file__"):
    # this happens under pyinstaller when running jdaviz cli
    # which triggers an error in astropy, so we set it to the
    # executable path of the cli executable
    sys.modules["__main__"].__file__ = sys.executable


from astropy.tests.runner import TestRunner

__all__ = ['__version__', 'test']

try:
    from .version import version as __version__
except ImportError:
    __version__ = ''

# Create the test function for self test
test = TestRunner.make_test_runner_in(os.path.dirname(__file__))
test = TestRunner.make_test_runner_in(os.path.dirname(__file__))
