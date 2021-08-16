import pytest
import tempfile
from zipfile import ZipFile
import pathlib

from astropy.utils.data import download_file

from jdaviz.configs.mosviz.helper import MosViz


@pytest.mark.remote_data
def test_niriss_parser(mosviz_app, tmpdir):

    test_data = 'https://stsci.box.com/shared/static/9lkf5zha6zkf8ujnairy6krobbh038wt.zip'
    fn = download_file(test_data, cache=True)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir)

    level3_path = (pathlib.Path(tmpdir) / 'NIRISS_for_parser_p0171')

    data_dir = level3_path

    mosviz_app.load_niriss_data(data_dir)

    assert len(mosviz_app.app.data_collection) == 80
    assert mosviz_app.app.data_collection[0].label == "Image canucs F150W"
    assert mosviz_app.app.data_collection[-1].label == "MOS Table"
