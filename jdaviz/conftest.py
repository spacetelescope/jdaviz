# This file is used to configure the behavior of pytest when using the Astropy
# test infrastructure.
import os

from astropy.version import version as astropy_version
if astropy_version < '3.0':
    from astropy.tests.pytest_plugins import *
    del pytest_report_header
else:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS


def pytest_configure(config):

    config.option.astropy_header = True

    PYTEST_HEADER_MODULES.pop('Pandas', None)
    PYTEST_HEADER_MODULES['scikit-image'] = 'skimage'

    from .version import version, astropy_helpers_version
    packagename = os.path.basename(os.path.dirname(__file__))
    TESTED_VERSIONS[packagename] = version
    TESTED_VERSIONS['astropy_helpers'] = astropy_helpers_version
