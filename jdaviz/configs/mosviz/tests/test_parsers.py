from zipfile import ZipFile
from tempfile import TemporaryDirectory
from pathlib import Path

import pytest
from astropy.utils.data import download_file

from jdaviz.utils import PRIHDR_KEY, COMMENTCARD_KEY


# This is another version of test_niriss_loader in test_data_loading.py
@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore', match="'(MJy/sr)^2' did not parse as fits unit")
def test_niriss_parser(mosviz_helper, tmpdir):
    '''
    Tests loading a NIRISS dataset
    This data set is a shortened version of the ERS program GLASS (Program 1324)
    provided by Camilla Pacifici. This is in-flight, "real" JWST data

    The spectra are jw01324001001_15101_00001_nis
    The direct image is jw01324-o001_t001_niriss_clear-f200w
    Please see JWST naming conventions for the above

    The dataset was uploaded to box by Duy Nguyen
    '''

    # Download data
    test_data = 'https://stsci.box.com/shared/static/cr14xijcg572dglacochctr1kblsr89a.zip'
    fn = download_file(test_data, cache=True, timeout=30)

    # Extract to a known, temporary folder
    data_dir = Path(TemporaryDirectory(dir=tmpdir).name)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(data_dir)

    mosviz_helper.load_data(directory=data_dir, instrument="niriss")
    assert len(mosviz_helper.app.data_collection) == 10

    # The image should be the first in the data collection
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == "Image jw01324-o001 F200W"
    assert PRIHDR_KEY not in dc_0.meta
    assert COMMENTCARD_KEY not in dc_0.meta
    assert dc_0.meta['bunit_data'] == 'MJy/sr'  # ASDF metadata

    # The MOS Table should be last in the data collection
    dc_tab = mosviz_helper.app.data_collection[-1]
    assert dc_tab.label == "MOS Table"
    assert len(dc_tab.meta) == 0

    # Test all the spectra exist
    for dispersion in ('R', 'C'):
        for sourceid in (243, 249):
            for spec_type in ('spec2d', 'spec1d'):
                data_label = f"F200W Source {sourceid} {spec_type} {dispersion}"
                data = mosviz_helper.app.data_collection[data_label]
                assert data.meta['SOURCEID'] == sourceid

                # Header should be imported from the spec2d files, not spec1d
                if spec_type == 'spec2d':
                    assert PRIHDR_KEY in data.meta
                    assert COMMENTCARD_KEY in data.meta
                else:
                    assert PRIHDR_KEY not in data.meta
                    assert COMMENTCARD_KEY in data.meta
                    assert 'header' not in data.meta
                    assert data.meta['FILTER'] == f'GR150{dispersion}'
