import pytest
import tempfile
from zipfile import ZipFile
import pathlib

from astropy.utils.data import download_file

from jdaviz.configs.mosviz.helper import MosViz

@pytest.fixture
def mosviz_helper():
    return MosViz()

@pytest.mark.remote_data
def test_niriss_parser(mosviz_helper):
    data_dir = tempfile.gettempdir()

    test_data = 'https://stsci.box.com/shared/static/9lkf5zha6zkf8ujnairy6krobbh038wt.zip'
    fn = download_file(test_data, cache=True)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(data_dir)

    level3_path = (pathlib.Path(data_dir) / 'NIRISS_for_parser_p0171')

    data_dir = level3_path

    mosviz_helper.load_niriss_data(data_dir)

    assert len(mosviz_helper.app.data_collection) == 80
    assert mosviz_helper.app.data_collection[0].label == "Image canucs F150W"
    assert mosviz_helper.app.data_collection[-1].label == "MOS Table"
