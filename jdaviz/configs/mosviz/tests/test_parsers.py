from zipfile import ZipFile

import pytest
from astropy.utils.data import download_file

from jdaviz.utils import PRIHDR_KEY, COMMENTCARD_KEY


@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore', match="'(MJy/sr)^2' did not parse as fits unit")
def test_niriss_parser(mosviz_helper, tmp_path):
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
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmp_path)

    mosviz_helper.load_data(directory=tmp_path, instrument="niriss")
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


@pytest.mark.remote_data
def test_missing_srctype(mosviz_helper, tmp_path):
    '''
    Tests that data missing the SRCTYPE keyword raises a warning to the user.

    SRCTYPE is required for Mosviz. We do not want to rely on the JWST x1d parser's
    default behavior of overwriting with "POINT" if it doesn't exist, as all NIRISS data
    should have this populated; missing SRCTYPE indicates something went wrong.

    This dataset was our original simulated NIRISS dataset that is missing SRCTYPE.

    NOTE: Under some conditions, a warning is raised when TemporaryDirectory attempts to
    clean itself up. Most likely a race condition between TempDir and pytest
    '''

    # Download data
    test_data = 'https://stsci.box.com/shared/static/l2azhcqd3tvzhybdlpx2j2qlutkaro3z.zip'
    fn = download_file(test_data, cache=True, timeout=30)

    # Extract to a known, temporary folder
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmp_path)

    with pytest.raises(KeyError, match=r".*The SRCTYPE keyword.*is not populated.*"):
        mosviz_helper.load_data(directory=(tmp_path / 'NIRISS_for_parser_p0171'),
                                instrument="niriss")
