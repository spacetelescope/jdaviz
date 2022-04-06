from zipfile import ZipFile
import pathlib

from astropy.utils.data import download_file
import numpy as np
import pytest
from jdaviz.configs.mosviz.helper import Mosviz


@pytest.fixture
def mosviz_helper():
    return Mosviz()


@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_multi_image_spec(mosviz_helper, image, spectrum1d, spectrum2d, label):
    spectra1d = [spectrum1d]*3
    spectra2d = [spectrum2d]*3
    images = [image]*3

    mosviz_helper.load_data(spectra1d, spectra2d, images=images, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 10

    qtable = mosviz_helper.to_table()
    if label is None:
        assert qtable["Images"][0] == "Image 0"
    else:
        assert qtable["Images"][0] == "Test Label 0"


@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_single_image_multi_spec(mosviz_helper, image, spectrum1d, spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [spectrum2d] * 3

    # Test that loading is still possible after previous crash:
    # https://github.com/spacetelescope/jdaviz/issues/364
    with pytest.raises(ValueError, match='The dimensions of component 2D Spectra are incompatible'):
        mosviz_helper.load_data(spectra1d, spectra2d, images=[])

    mosviz_helper.load_data(spectra1d, spectra2d, images=image, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 8

    qtable = mosviz_helper.to_table()
    if label is None:
        assert np.all(qtable["Images"] == "Shared Image")
    else:
        assert np.all(qtable["Images"] == "Test Label")
    assert len(qtable) == 3

@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_niriss_directory(mosviz_helper, tmpdir):

    test_data = 'https://stsci.box.com/shared/static/l2azhcqd3tvzhybdlpx2j2qlutkaro3z.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir)

    level3_path = (pathlib.Path(tmpdir) / 'NIRISS_for_parser_p0171')

    data_dir = level3_path

    mosviz_helper.load_niriss_data(data_dir)

    assert len(mosviz_helper.app.data_collection) == 80
    assert mosviz_helper.app.data_collection[0].label == "Image canucs F150W"
    assert mosviz_helper.app.data_collection[-1].label == "MOS Table"
