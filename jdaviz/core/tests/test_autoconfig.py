# Tests automatic config detection against our example notebook data

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from astroquery.mast import Observations
from astropy.utils.data import download_file
from ipyvuetify import Sheet

from jdaviz import open as jdaviz_open
from jdaviz.cli import ALL_JDAVIZ_CONFIGS
from jdaviz.configs import Specviz2d, Cubeviz, Imviz  # , Specviz
from jdaviz.core.launcher import Launcher, STATUS_HINTS


AUTOCONFIG_EXAMPLES = (
    # ("mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits", Specviz),
    # Specviz check disabled due to https://github.com/spacetelescope/jdaviz/issues/2229
    ("mast:JWST/product/jw01538-o160_s00004_nirspec_f170lp-g235h-s1600a1-sub2048_s2d.fits", Specviz2d),  # noqa
    ("mast:JWST/product/jw02727-o002_t062_nircam_clear-f090w_i2d.fits", Imviz),
    ("mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_s3d.fits", Cubeviz),
    ("https://stsci.box.com/shared/static/28a88k1qfipo4yxc4p4d40v4axtlal8y.fits", Cubeviz)
    # Check that MaNGA cubes go to cubeviz. This file is originally from:
    # https://data.sdss.org/sas/dr14/manga/spectro/redux/v2_1_2/7495/stack/manga-7495-12704-LOGCUBE.fits.gz)
)

@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('uris', AUTOCONFIG_EXAMPLES)
def test_autoconfig(uris):
    # Setup temporary directory
    with TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
        uri = uris[0]
        helper_class = uris[1]

        if uri.startswith("mast:"):
            download_path = str(Path(tempdir) / Path(uri).name)
            Observations.download_file(uri, local_path=download_path)
        elif uri.startswith("http"):
            download_path = download_file(uri, cache=True, timeout=100)

        viz_helper = jdaviz_open(download_path, show=False)

        assert isinstance(viz_helper, helper_class)
        assert len(viz_helper.app.data_collection) > 0

@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore')
def test_launcher():
    launcher = Launcher(None, ALL_JDAVIZ_CONFIGS)

    # Test starting state
    assert launcher.hint == STATUS_HINTS['idle']
    assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS

    # Test invalid filepath
    launcher.filepath = "ThisIsAFakeFileNameThatShouldNotExist"
    assert launcher.hint == STATUS_HINTS['invalid path']
    assert len(launcher.compatible_configs) == 0

    # Test reseting to empty state
    launcher.filepath = ""
    assert launcher.hint == STATUS_HINTS['idle']
    assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS

    # Test with real files
    # Setup temporary directory
    with TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
        for uri, config in AUTOCONFIG_EXAMPLES:
            if uri.startswith("mast:"):
                download_path = str(Path(tempdir) / Path(uri).name)
                Observations.download_file(uri, local_path=download_path)
            elif uri.startswith("http"):
                download_path = download_file(uri, cache=True, timeout=100)
            launcher.filepath = download_path
            # In testing, setting the filepath will stall until identifying is complete
            # No need to be concerned for race condition here
            assert launcher.hint == STATUS_HINTS['id ok']
            assert launcher.compatible_configs == [config().__class__.__name__.lower()]

    # Test reseting to empty state
    launcher.filepath = ""
    assert launcher.hint == STATUS_HINTS['idle']
    assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS   
