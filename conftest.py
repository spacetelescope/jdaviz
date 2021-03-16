# This copies over some pytest setup from jdaviz/conftest.py so tox can see it.

try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
    ASTROPY_HEADER = True
except ImportError:
    ASTROPY_HEADER = False


def pytest_configure(config):

    if ASTROPY_HEADER:

        config.option.astropy_header = True

        # Customize the following lines to add/remove entries from the list of
        # packages for which version numbers are displayed when running the tests.
        PYTEST_HEADER_MODULES['astropy'] = 'astropy'
        PYTEST_HEADER_MODULES['pyyaml'] = 'yaml'
        PYTEST_HEADER_MODULES['specutils'] = 'specutils'
        PYTEST_HEADER_MODULES['spectral-cube'] = 'spectral_cube'
        PYTEST_HEADER_MODULES['asteval'] = 'asteval'
        PYTEST_HEADER_MODULES['click'] = 'click'
        PYTEST_HEADER_MODULES['echo'] = 'echo'
        PYTEST_HEADER_MODULES['traitlets'] = 'traitlets'
        PYTEST_HEADER_MODULES['glue-core'] = 'glue'
        PYTEST_HEADER_MODULES['glue-jupyter'] = 'glue_jupyter'
        PYTEST_HEADER_MODULES['glue-astronomy'] = 'glue_astronomy'
        PYTEST_HEADER_MODULES['ipyvue'] = 'ipyvue'
        PYTEST_HEADER_MODULES['ipyvuetify'] = 'ipyvuetify'
        PYTEST_HEADER_MODULES['ipysplitpanes'] = 'ipysplitpanes'
        PYTEST_HEADER_MODULES['ipygoldenlayout'] = 'ipygoldenlayout'
        PYTEST_HEADER_MODULES['voila'] = 'voila'
        PYTEST_HEADER_MODULES['vispy'] = 'vispy'

        from jdaviz import __version__
        TESTED_VERSIONS['jdaviz'] = __version__


# Uncomment the last two lines in this block to treat all DeprecationWarnings as
# exceptions.
# from astropy.tests.helper import enable_deprecations_as_exceptions
# enable_deprecations_as_exceptions()
