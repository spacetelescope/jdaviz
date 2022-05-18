from zipfile import ZipFile
import pathlib

import pytest
from astropy.utils.data import download_file

from jdaviz.utils import PRIHDR_KEY, COMMENTCARD_KEY


# This is another version of test_niriss_loader in test_data_loading.py
@pytest.mark.remote_data
def test_niriss_parser(mosviz_helper, tmpdir):

    test_data = 'https://stsci.box.com/shared/static/l2azhcqd3tvzhybdlpx2j2qlutkaro3z.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir)

    level3_path = (pathlib.Path(tmpdir) / 'NIRISS_for_parser_p0171')

    data_dir = level3_path

    mosviz_helper.load_niriss_data(data_dir)

    assert len(mosviz_helper.app.data_collection) == 80

    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == "Image canucs F150W"
    assert PRIHDR_KEY not in dc_0.meta
    assert COMMENTCARD_KEY not in dc_0.meta
    assert dc_0.meta['bunit_data'] == 'MJy/sr'  # ASDF metadata

    dc_1 = mosviz_helper.app.data_collection[1]
    assert dc_1.label == 'F150W Source 1 spec2d C'
    assert PRIHDR_KEY in dc_1.meta
    assert COMMENTCARD_KEY in dc_1.meta
    assert dc_1.meta['SOURCEID'] == 1

    dc_40 = mosviz_helper.app.data_collection[40]
    assert dc_40.label == 'F150W Source 1 spec1d C'
    assert PRIHDR_KEY not in dc_40.meta
    assert COMMENTCARD_KEY in dc_40.meta
    assert 'header' not in dc_40.meta
    assert dc_40.meta['FILTER'] == 'GR150C'

    dc_tab = mosviz_helper.app.data_collection[-1]
    assert dc_tab.label == "MOS Table"
    assert len(dc_tab.meta) == 0
