# Tests data loading in the Mosviz Jdaviz configuration

import pathlib
from zipfile import ZipFile

from astropy.nddata import CCDData
from astropy.utils.data import download_file
import numpy as np
import pytest
from specutils import Spectrum1D

from jdaviz.utils import PRIHDR_KEY


def test_load_spectrum1d(mosviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    mosviz_helper.load_data(spectra_1d=spectrum1d, spectra_1d_label=label)

    assert len(mosviz_helper.app.data_collection) == 2
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == label
    assert dc_0.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(data[label], Spectrum1D)

    with pytest.raises(AttributeError):
        mosviz_helper.load_1d_spectra([1, 2, 3])


@pytest.mark.filterwarnings('ignore')
def test_load_image(mosviz_helper, mos_image):
    label = "Test Image"
    mosviz_helper.load_images(mos_image, data_labels=label)

    assert len(mosviz_helper.app.data_collection) == 2
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == f"{label} 0"
    assert PRIHDR_KEY not in dc_0.meta
    assert dc_0.meta['RADESYS'] == 'ICRS'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('image-viewer')

    dataval = data[f"{label} 0"]
    assert isinstance(dataval, CCDData)
    assert dataval.shape == (55, 55)


def test_load_spectrum_collection(mosviz_helper, spectrum_collection):
    labels = [f"Test Spectrum Collection {i}" for i in range(5)]
    mosviz_helper.load_1d_spectra(spectrum_collection, data_labels=labels)

    assert len(mosviz_helper.app.data_collection) == 6
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == labels[0]
    assert dc_0.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(data[labels[0]], Spectrum1D)


def test_load_list_of_spectrum1d(mosviz_helper, spectrum1d):
    spectra = [spectrum1d] * 3

    labels = [f"Test Spectrum 1D {i}" for i in range(3)]
    mosviz_helper.load_1d_spectra(spectra, data_labels=labels)

    assert len(mosviz_helper.app.data_collection) == 4
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == labels[0]
    assert dc_0.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(data[labels[0]], Spectrum1D)


@pytest.mark.filterwarnings('ignore')
def test_load_mos_spectrum2d(mosviz_helper, mos_spectrum2d):

    label = "Test 2D Spectrum"
    mosviz_helper.load_data(spectra_2d=mos_spectrum2d, spectra_2d_label=label)

    assert len(mosviz_helper.app.data_collection) == 2
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == label
    assert dc_0.meta['INSTRUME'] == 'nirspec'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-2d-viewer')

    assert data[label].shape == (1024, 15)


@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_multi_image_spec(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [mos_spectrum2d] * 3
    images = [mos_image] * 3

    mosviz_helper.load_data(spectra1d, spectra2d, images=images, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 10

    qtable = mosviz_helper.to_table()
    if label is None:
        assert qtable["Images"][0] == "Image 0"
    else:
        assert qtable["Images"][0] == "Test Label 0"


def test_load_multi_image_and_spec1d_only(mosviz_helper, mos_image, spectrum1d):
    spectra1d = [spectrum1d] * 3
    images = [mos_image] * 3

    mosviz_helper.load_data(spectra_1d=spectra1d, images=images)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 7


def test_load_multi_image_and_spec2d_only(mosviz_helper, mos_image, mos_spectrum2d):
    spectra2d = [mos_spectrum2d] * 3
    images = [mos_image] * 3

    mosviz_helper.load_data(spectra_2d=spectra2d, images=images)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 7


@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_single_image_multi_spec(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [mos_spectrum2d] * 3

    # Test that loading is still possible after previous crash:
    # https://github.com/spacetelescope/jdaviz/issues/364
    with pytest.raises(ValueError, match='The dimensions of component 2D Spectra are incompatible'):
        mosviz_helper.load_data(spectra1d, spectra2d, images=[])

    mosviz_helper.load_data(spectra1d, spectra2d, images=mos_image, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 8

    qtable = mosviz_helper.to_table()
    if label is None:
        assert np.all(qtable["Images"] == "Shared Image")
    else:
        assert np.all(qtable["Images"] == "Test Label")
    assert len(qtable) == 3


@pytest.mark.filterwarnings('ignore')
@pytest.mark.remote_data
def test_nirspec_loader(mosviz_helper, tmpdir):
    '''
    Tests loading our default MosvizExample notebook data
    '''

    test_data = 'https://stsci.box.com/shared/static/ovyxi5eund92yoadvv01mynwt8t5n7jv.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir)

    level3_path = (pathlib.Path(tmpdir) / 'mosviz_nirspec_data_0.3' / 'level3')

    data_dir = level3_path

    mosviz_helper.load_data(directory=data_dir, instrument='nirspec')

    assert len(mosviz_helper.app.data_collection) == 16

    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == "MOS Table"
    assert len(dc_0.meta) == 0

    dc_5 = mosviz_helper.app.data_collection[5]
    assert dc_5.label == "Image 4"
    assert PRIHDR_KEY not in dc_5.meta
    assert dc_5.meta['WCSAXES'] == 2

    dc_10 = mosviz_helper.app.data_collection[10]
    assert dc_10.label == "1D Spectrum 4"
    assert PRIHDR_KEY not in dc_10.meta
    assert 'header' not in dc_10.meta
    assert dc_10.meta['TARGNAME'] == 'FOO'

    dc_15 = mosviz_helper.app.data_collection[15]
    assert dc_15.label == "2D Spectrum 4"
    assert PRIHDR_KEY not in dc_15.meta
    assert 'header' not in dc_15.meta
    assert dc_15.meta['SOURCEID'] == 2315


@pytest.mark.remote_data
def test_nirspec_fallback(mosviz_helper, tmpdir):
    '''
    When no instrument is provided, mosviz.load_data is expected to fallback to the nirspec loader.
    Naturally, the nirspec dataset should then work without any instrument keyword
    '''

    test_data = 'https://stsci.box.com/shared/static/ovyxi5eund92yoadvv01mynwt8t5n7jv.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir)

    level3_path = (pathlib.Path(tmpdir) / 'mosviz_nirspec_data_0.3' / 'level3')

    data_dir = level3_path
    with pytest.warns(UserWarning, match="Ambiguous MOS Instrument"):
        mosviz_helper.load_data(directory=data_dir)

    assert len(mosviz_helper.app.data_collection) == 16
    assert "MOS Table" in mosviz_helper.app.data_collection
    assert "Image 4" in mosviz_helper.app.data_collection
    assert "1D Spectrum 4" in mosviz_helper.app.data_collection
    assert "2D Spectrum 4" in mosviz_helper.app.data_collection


def test_zip_error(mosviz_helper, tmp_path):
    '''
    Zipfiles are explicitly and intentionally not supported. This test confirms a TypeError is
    raised if the user tries to supply a Zipfile and expects Mosviz to autoextract.
    '''
    zip_path = tmp_path / "jdaviz_test_zip.zip"
    zip = ZipFile(zip_path, mode='w')
    zip.close()

    with pytest.raises(TypeError, match="Please extract"):
        mosviz_helper.load_data(directory=str(zip_path))
