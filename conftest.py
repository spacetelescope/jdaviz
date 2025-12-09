from jdaviz import __version__
from jdaviz.pytest_memlog import (memlog_addoption, memlog_configure, memlog_runtest_setup,
                                  memlog_runtest_teardown, memlog_runtest_makereport,
                                  memlog_runtest_logreport, memlog_terminal_summary)


# ============================================================================
# Memory logging plugin (memlog) - imported from pytest_memlog.py
# ============================================================================
def pytest_addoption(parser):
    """
    Register pytest options.
    """
    memlog_addoption(parser)


def pytest_runtest_setup(item):
    """
    Setup hook that records memory before test.
    """
    memlog_runtest_setup(item)


def pytest_runtest_teardown(item, nextitem):
    """
    Teardown hook that records memory after test.
    """
    memlog_runtest_teardown(item, nextitem)


# Re-export the hookwrapper directly
pytest_runtest_makereport = memlog_runtest_makereport


def pytest_runtest_logreport(report):
    """
    Log report hook that collects memory measurements from user_properties.
    """
    memlog_runtest_logreport(report)


def pytest_terminal_summary(terminalreporter, config=None):
    """
    Terminal summary hook that prints memlog summary.
    """
    memlog_terminal_summary(terminalreporter, config)


try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
except ImportError:
    PYTEST_HEADER_MODULES = {}
    TESTED_VERSIONS = {}


# This is repeated from jdaviz/conftest.py because tox cannot grab test
# header from that file.
def pytest_configure(config):
    # Initialize memlog
    memlog_configure(config)

    PYTEST_HEADER_MODULES['astropy'] = 'astropy'
    PYTEST_HEADER_MODULES['pyyaml'] = 'yaml'
    PYTEST_HEADER_MODULES['scikit-image'] = 'skimage'
    PYTEST_HEADER_MODULES['specutils'] = 'specutils'
    PYTEST_HEADER_MODULES['specreduce'] = 'specreduce'
    PYTEST_HEADER_MODULES['asteval'] = 'asteval'
    PYTEST_HEADER_MODULES['echo'] = 'echo'
    PYTEST_HEADER_MODULES['idna'] = 'idna'
    PYTEST_HEADER_MODULES['traitlets'] = 'traitlets'
    PYTEST_HEADER_MODULES['bqplot'] = 'bqplot'
    PYTEST_HEADER_MODULES['bqplot-image-gl'] = 'bqplot_image_gl'
    PYTEST_HEADER_MODULES['glue-core'] = 'glue'
    PYTEST_HEADER_MODULES['glue-jupyter'] = 'glue_jupyter'
    PYTEST_HEADER_MODULES['glue-astronomy'] = 'glue_astronomy'
    PYTEST_HEADER_MODULES['ipyvue'] = 'ipyvue'
    PYTEST_HEADER_MODULES['ipyvuetify'] = 'ipyvuetify'
    PYTEST_HEADER_MODULES['ipysplitpanes'] = 'ipysplitpanes'
    PYTEST_HEADER_MODULES['ipygoldenlayout'] = 'ipygoldenlayout'
    PYTEST_HEADER_MODULES['ipypopout'] = 'ipypopout'
    PYTEST_HEADER_MODULES['solara'] = 'solara'
    PYTEST_HEADER_MODULES['vispy'] = 'vispy'
    PYTEST_HEADER_MODULES['gwcs'] = 'gwcs'
    PYTEST_HEADER_MODULES['asdf'] = 'asdf'
    PYTEST_HEADER_MODULES['stdatamodels'] = 'stdatamodels'
    PYTEST_HEADER_MODULES['roman_datamodels'] = 'roman_datamodels'

    TESTED_VERSIONS['jdaviz'] = __version__
