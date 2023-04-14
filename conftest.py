from jdaviz import __version__

try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
except ImportError:
    PYTEST_HEADER_MODULES = {}
    TESTED_VERSIONS = {}


# This is repeated from jdaviz/conftest.py because tox cannot grab test
# header from that file.
def pytest_configure(config):
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
    PYTEST_HEADER_MODULES['voila'] = 'voila'
    PYTEST_HEADER_MODULES['vispy'] = 'vispy'
    PYTEST_HEADER_MODULES['gwcs'] = 'gwcs'
    PYTEST_HEADER_MODULES['asdf'] = 'asdf'
    PYTEST_HEADER_MODULES['stdatamodels'] = 'stdatamodels'
    PYTEST_HEADER_MODULES['roman_datamodels'] = 'roman_datamodels'

    TESTED_VERSIONS['jdaviz'] = __version__
