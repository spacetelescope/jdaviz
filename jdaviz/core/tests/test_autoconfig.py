# Tests automatic config detection against our example notebook data

from pathlib import Path

import pytest
from astroquery.mast import Observations
from astropy.utils.data import download_file

from jdaviz import open as jdaviz_open
from jdaviz.cli import ALL_JDAVIZ_CONFIGS
from jdaviz.configs import Specviz2d, Cubeviz, Imviz, Specviz
from jdaviz.core.launcher import Launcher, STATUS_HINTS
from jdaviz.utils import cached_uri


AUTOCONFIG_EXAMPLES = (
    ("mast:JWST/product/jw02732004001_02103_00004_mirifushort_x1d.fits", Specviz),
    ("mast:JWST/product/jw01538160001_16101_00004_nrs1_s2d.fits", Specviz2d),
    ("mast:JWST/product/jw02727-o002_t062_nircam_clear-f090w_i2d.fits", Imviz),
    ("mast:JWST/product/jw02732004001_02103_00004_mirifushort_s3d.fits", Cubeviz),
    ("https://stsci.box.com/shared/static/28a88k1qfipo4yxc4p4d40v4axtlal8y.fits", Cubeviz)
    # Check that MaNGA cubes go to cubeviz. This file is originally from:
    # https://data.sdss.org/sas/dr14/manga/spectro/redux/v2_1_2/7495/stack/manga-7495-12704-LOGCUBE.fits.gz)
)


@pytest.mark.remote_data
@pytest.mark.slow
@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('uris', AUTOCONFIG_EXAMPLES)
def test_autoconfig(uris):
    uri = uris[0]
    helper_class = uris[1]

    kwargs = dict(cache=True, show=False)

    viz_helper = jdaviz_open(cached_uri(uri), **kwargs)
    assert isinstance(viz_helper, helper_class)
    assert len(viz_helper.app.data_collection) > 0


@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore')
def test_launcher(tmp_path):
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
    for uri, config in AUTOCONFIG_EXAMPLES:
        uri = cached_uri(uri)
        if uri.startswith("mast:"):
            download_path = str(tmp_path / Path(uri).name)
            Observations.download_file(uri, local_path=download_path)
        elif uri.startswith("http"):
            download_path = download_file(uri, cache=True, timeout=100)
        else:
            # cached local file
            download_path = uri
        launcher.filepath = download_path
        # In testing, setting the filepath will stall until identifying is complete
        # No need to be concerned for race condition here
        assert launcher.hint == STATUS_HINTS['id ok']
        assert launcher.compatible_configs == [config().__class__.__name__.lower()]

    # Test reseting to empty state
    launcher.filepath = ""
    assert launcher.hint == STATUS_HINTS['idle']
    assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS
