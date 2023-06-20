# Tests data loading in the Mosviz Jdaviz configuration

from zipfile import ZipFile

import numpy as np
import pytest
from astropy.nddata import CCDData
from specutils import Spectrum1D

from jdaviz.utils import PRIHDR_KEY


def test_load_spectrum1d(mosviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    mosviz_helper.load_data(spectra_1d=spectrum1d, spectra_1d_label=label)

    assert len(mosviz_helper.app.data_collection) == 2
    assert mosviz_helper.app.data_collection[0].label == "MOS Table"
    dc_1 = mosviz_helper.app.data_collection[1]
    assert dc_1.label == label
    assert dc_1.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name)
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_viewer(mosviz_helper._default_spectrum_viewer_reference_name
                                        ).data()

    assert len(data) == 1
    assert isinstance(data[0], Spectrum1D)

    with pytest.raises(AttributeError):
        mosviz_helper.load_1d_spectra([1, 2, 3])


def test_load_image(mosviz_helper, mos_image):
    label = "Test Image"
    mosviz_helper.load_images(mos_image, data_labels=label, add_redshift_column=True)

    assert len(mosviz_helper.app.data_collection) == 2
    assert mosviz_helper.app.data_collection[0].label == "MOS Table"
    dc_1 = mosviz_helper.app.data_collection[1]
    assert dc_1.label == f"{label} 0"
    assert PRIHDR_KEY not in dc_1.meta
    assert dc_1.meta['RADESYS'] == 'ICRS'

    table = mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name)
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_viewer(mosviz_helper._default_image_viewer_reference_name
                                        ).data(cls=CCDData)

    assert len(data) == 1
    dataval = data[0]
    assert isinstance(dataval, CCDData)
    assert dataval.shape == (55, 55)


def test_load_spectrum_collection(mosviz_helper, spectrum_collection):
    labels = [f"Test Spectrum Collection {i}" for i in range(5)]
    mosviz_helper.load_1d_spectra(spectrum_collection, data_labels=labels, add_redshift_column=True)

    # +1 for the table viewer
    assert len(mosviz_helper.app.data_collection) == len(spectrum_collection) + 1
    assert mosviz_helper.app.data_collection[0].label == "MOS Table"
    dc_1 = mosviz_helper.app.data_collection[1]
    assert dc_1.label == labels[0]
    assert dc_1.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name)
    table.select_row(0)

    data = mosviz_helper.app.get_viewer(mosviz_helper._default_spectrum_viewer_reference_name
                                        ).data()

    assert len(data) == 1
    assert isinstance(data[0], Spectrum1D)


def test_load_list_of_spectrum1d(mosviz_helper, spectrum1d):
    spectra = [spectrum1d] * 3

    labels = [f"Test Spectrum 1D {i}" for i in range(3)]
    mosviz_helper.load_1d_spectra(spectra, data_labels=labels, add_redshift_column=True)

    assert len(mosviz_helper.app.data_collection) == 4
    assert mosviz_helper.app.data_collection[0].label == "MOS Table"
    dc_1 = mosviz_helper.app.data_collection[1]
    assert dc_1.label == labels[0]
    assert dc_1.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name)
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_viewer(mosviz_helper._default_spectrum_viewer_reference_name
                                        ).data()

    assert len(data) == 1
    assert isinstance(data[0], Spectrum1D)


def test_load_mos_spectrum2d(mosviz_helper, mos_spectrum2d):

    label = "Test 2D Spectrum"
    mosviz_helper.load_data(spectra_2d=mos_spectrum2d, spectra_2d_label=label)

    assert len(mosviz_helper.app.data_collection) == 2
    assert mosviz_helper.app.data_collection[0].label == "MOS Table"
    dc_1 = mosviz_helper.app.data_collection[1]
    assert dc_1.label == label
    assert dc_1.meta['INSTRUME'] == 'nirspec'

    table = mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name)
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_viewer(mosviz_helper._default_spectrum_2d_viewer_reference_name
                                        ).data()

    assert len(data) == 1
    assert data[0].shape == (1024, 15)


@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_multi_image_spec(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [mos_spectrum2d] * 3
    images = [mos_image] * 3

    mosviz_helper.load_data(spectra1d, spectra2d, images=images, images_label=label)

    assert mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name
                                        ).figure_widget.highlighted == 0
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

    assert mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name
                                        ).figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 7


def test_load_multi_image_and_spec2d_only(mosviz_helper, mos_image, mos_spectrum2d):
    spectra2d = [mos_spectrum2d] * 3
    images = [mos_image] * 3

    mosviz_helper.load_data(spectra_2d=spectra2d, images=images)

    assert mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name
                                        ).figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 7


@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_single_image_multi_spec(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [mos_spectrum2d] * 3

    image_viewer = mosviz_helper.app.get_viewer('image-viewer')
    spec1d_viewer = mosviz_helper.app.get_viewer('spectrum-viewer')
    spec2d_viewer = mosviz_helper.app.get_viewer('spectrum-2d-viewer')

    # Coordinates info panel should not crash even when nothing is loaded.
    label_mouseover = mosviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(image_viewer, {'event': 'mousemove',
                                                       'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ('', '', '')

    # Test that loading is still possible after previous crash:
    # https://github.com/spacetelescope/jdaviz/issues/364
    with pytest.raises(ValueError, match="incompatible with the dimensions of this data:"):
        mosviz_helper.load_data(spectra1d, spectra2d, images=[mos_image, mos_image])

    mosviz_helper.load_data(spectra1d, spectra2d, images=mos_image, images_label=label)

    assert mosviz_helper.app.get_viewer(mosviz_helper._default_table_viewer_reference_name
                                        ).figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 8

    qtable = mosviz_helper.to_table()
    if label is None:
        assert np.all(qtable["Images"] == "Shared Image")
    else:
        assert np.all(qtable["Images"] == "Test Label")
    assert len(qtable) == 3

    # Also check coordinates info panels for Mosviz image viewer.
    # 1D spectrum viewer panel is also tested in Specviz.
    # 2D spectrum viewer panel is also tested in Specviz2d.

    label_mouseover._viewer_mouse_event(image_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ('Pixel x=000.0 y=000.0 Value +3.74540e-01 Jy',
                                         'World 00h20m07.1483s +04d59m30.8371s (ICRS)',
                                         '5.0297844783 4.9918991917 (deg)')
    assert label_mouseover.icon == 'a'

    label_mouseover._viewer_mouse_event(image_viewer,
                                        {'event': 'mousemove', 'domain': {'x': None, 'y': 0}})
    assert label_mouseover.as_text() == ('', '', '')
    assert label_mouseover.icon == ''

    label_mouseover._viewer_mouse_event(image_viewer,
                                        {'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert label_mouseover.as_text() == ('Pixel x=-01.0 y=000.0',
                                         'World 00h20m07.1519s +04d59m30.8371s (ICRS)',
                                         '5.0297997183 4.9918991914 (deg)')

    label_mouseover._viewer_mouse_event(image_viewer, {'event': 'mouseleave'})
    assert label_mouseover.as_text() == ('', '', '')
    assert label_mouseover.icon == ''

    label_mouseover._viewer_mouse_event(spec2d_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 10, 'y': 100}})
    assert label_mouseover.as_text() == ('Pixel x=00010.0 y=00100.0 Value +8.12986e-01', '', '')
    assert label_mouseover.icon == 'c'

    # need to trigger a mouseleave or mouseover to reset the traitlets
    label_mouseover._viewer_mouse_event(spec1d_viewer, {'event': 'mouseenter'})
    label_mouseover._viewer_mouse_event(spec1d_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 7000, 'y': 170}})
    assert label_mouseover.as_text() == ('Cursor 7.00000e+03, 1.70000e+02',
                                         'Wave 6.88889e+03 Angstrom (4 pix)',
                                         'Flux 1.35436e+01 Jy')
    assert label_mouseover.icon == 'b'


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


def test_invalid_inputs(mosviz_helper):
    with pytest.raises(NotImplementedError, match=r".*not a directory"):
        mosviz_helper.load_data(directory="foo")

    with pytest.raises(NotImplementedError, match="Please set valid values"):
        mosviz_helper.load_data()
