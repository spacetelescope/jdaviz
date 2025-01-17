import pytest

import numpy as np
from astropy import units as u
from astropy.wcs import WCS
from specutils import Spectrum1D
from jdaviz import Application, Specviz
from jdaviz.configs.default.plugins.gaussian_smooth.gaussian_smooth import GaussianSmooth
from jdaviz.core.unit_conversion_utils import (flux_conversion_general,
                                               viewer_flux_conversion_equivalencies)


# This applies to all viz but testing with Imviz should be enough.
def test_viewer_calling_app(imviz_helper):
    viewer = imviz_helper.default_viewer._obj
    assert viewer.session.jdaviz_app is imviz_helper.app


def test_get_tray_item_from_name():
    app = Application(configuration='default')
    plg = app.get_tray_item_from_name('g-gaussian-smooth')
    assert isinstance(plg, GaussianSmooth)

    with pytest.raises(KeyError, match='not found in app'):
        app.get_tray_item_from_name('imviz-compass')


def test_nonstandard_specviz_viewer_name(spectrum1d):
    config = {'settings': {'configuration': 'nonstandard',
                           'data': {'parser': 'specviz-spectrum1d-parser'},
                           'visible': {'menu_bar': False,
                                       'toolbar': True,
                                       'tray': True,
                                       'tab_headers': False},
                           'context': {'notebook': {'max_height': '750px'}}},
              'toolbar': ['g-data-tools', 'g-subset-tools'],
              'tray': ['g-metadata-viewer',
                       'g-plot-options',
                       'g-subset-tools',
                       'g-gaussian-smooth',
                       'g-model-fitting',
                       'g-unit-conversion',
                       'g-line-list',
                       'specviz-line-analysis',
                       'export'],
              'viewer_area': [{'container': 'col',
                               'children': [{'container': 'row',
                                             'viewers': [{'name': 'H',
                                                          'plot': 'specviz-profile-viewer',
                                                          'reference': 'h'},
                                                         {'name': 'K',
                                                          'plot': 'specviz-profile-viewer',
                                                          'reference': 'k'}]}]}]}

    class Customviz(Specviz):
        _default_configuration = config
        _default_spectrum_viewer_reference_name = 'h'

    viz = Customviz()
    assert viz.app.get_viewer_reference_names() == ['h', 'k']

    viz.load_data(spectrum1d, data_label='example label')
    with pytest.raises(ValueError):
        viz.get_data("non-existent label")


def test_duplicate_data_labels(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="test")
    specviz_helper.load_data(spectrum1d, data_label="test")
    dc = specviz_helper.app.data_collection
    assert dc[0].label == "test"
    assert dc[1].label == "test (1)"
    specviz_helper.load_data(spectrum1d, data_label="test_1")
    specviz_helper.load_data(spectrum1d, data_label="test")
    assert dc[2].label == "test_1"
    assert dc[3].label == "test (2)"


def test_duplicate_data_labels_with_brackets(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="test[test]")
    specviz_helper.load_data(spectrum1d, data_label="test[test]")
    dc = specviz_helper.app.data_collection
    assert len(dc) == 2
    assert dc[0].label == "test[test]"
    assert dc[1].label == "test[test] (1)"


def test_return_data_label_is_none(specviz_helper):
    data_label = specviz_helper.app.return_data_label(None)
    assert data_label == "Unknown"


def test_return_data_label_is_image(specviz_helper):
    data_label = specviz_helper.app.return_data_label("data/path/test.jpg")
    assert data_label == "test[jpg]"


def test_hdulist_with_filename(cubeviz_helper, image_cube_hdu_obj):
    image_cube_hdu_obj.file_name = "test"
    data_label = cubeviz_helper.app.return_data_label(image_cube_hdu_obj)
    assert data_label == "test[HDU object]"


def test_file_path_not_image(imviz_helper, tmp_path):
    path = tmp_path / "myimage.fits"
    path.touch()
    data_label = imviz_helper.app.return_data_label(str(path))
    assert data_label == "myimage"


def test_unique_name_variations(specviz_helper, spectrum1d):
    data_label = specviz_helper.app.return_unique_name(None)
    assert data_label == "Unknown"

    specviz_helper.load_data(spectrum1d, data_label="test[flux]")
    data_label = specviz_helper.app.return_data_label("test[flux]", ext="flux")
    assert data_label == "test[flux][flux]"

    data_label = specviz_helper.app.return_data_label("test", ext="flux")
    assert data_label == "test[flux] (1)"


def test_substring_in_label(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="M31")
    specviz_helper.load_data(spectrum1d, data_label="M32")
    data_label = specviz_helper.app.return_data_label("M")
    assert data_label == "M"


@pytest.mark.parametrize('data_label', ('111111', 'aaaaa', '///(#$@)',
                                        'two  spaces  repeating',
                                        'word42word42word  two  spaces'))
def test_edge_cases(specviz_helper, spectrum1d, data_label):
    dc = specviz_helper.app.data_collection

    specviz_helper.load_data(spectrum1d, data_label=data_label)
    specviz_helper.load_data(spectrum1d, data_label=data_label)
    assert dc[1].label == f"{data_label} (1)"

    specviz_helper.load_data(spectrum1d, data_label=data_label)
    assert dc[2].label == f"{data_label} (2)"


def test_case_that_used_to_break_return_label(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="this used to break (1)")
    specviz_helper.load_data(spectrum1d, data_label="this used to break")
    dc = specviz_helper.app.data_collection
    assert dc[0].label == "this used to break (1)"
    assert dc[1].label == "this used to break (2)"


def test_viewer_renaming_specviz(specviz_helper):
    viewer_names = [
        'spectrum-viewer',
        'second-viewer-name',
        'third-viewer-name'
    ]

    for i in range(len(viewer_names) - 1):
        specviz_helper.app._update_viewer_reference_name(
            old_reference=viewer_names[i],
            new_reference=viewer_names[i + 1]
        )
        assert specviz_helper.app.get_viewer(viewer_names[i+1]) is not None


def test_viewer_renaming_imviz(imviz_helper):
    with pytest.raises(ValueError, match="'imviz-0' cannot be changed"):
        imviz_helper.app._update_viewer_reference_name(
            old_reference='imviz-0',
            new_reference='this-is-forbidden'
        )

    with pytest.raises(ValueError, match="does not exist"):
        imviz_helper.app._update_viewer_reference_name(
            old_reference='non-existent',
            new_reference='this-is-forbidden'
        )


def test_data_associations(imviz_helper):
    shape = (10, 10)

    data_parent = np.ones(shape, dtype=float)
    data_child = np.zeros(shape, dtype=int)

    imviz_helper.load_data(data_parent, data_label='parent_data')
    imviz_helper.load_data(data_child, data_label='child_data', parent='parent_data')

    assert imviz_helper.app._get_assoc_data_children('parent_data') == ['child_data']
    assert imviz_helper.app._get_assoc_data_parent('child_data') == 'parent_data'

    with pytest.raises(NotImplementedError):
        # we don't (yet) allow children of children:
        imviz_helper.load_data(data_child, data_label='grandchild_data', parent='child_data')

    with pytest.raises(ValueError):
        # ensure the parent actually exists:
        imviz_helper.load_data(data_child, data_label='child_data', parent='absent parent')


def test_to_unit(cubeviz_helper):
    # custom cube to have Surface Brightness units
    wcs_dict = {"CTYPE1": "WAVE-LOG", "CTYPE2": "DEC--TAN", "CTYPE3": "RA---TAN",
                "CRVAL1": 4.622e-7, "CRVAL2": 27, "CRVAL3": 205,
                "CDELT1": 8e-11, "CDELT2": 0.0001, "CDELT3": -0.0001,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0, "PIXAR_SR": 8e-11}
    w = WCS(wcs_dict)
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * (u.MJy / u.sr), wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    # this can be removed once spectra pass through spectral extraction
    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = extract_plg.aperture.choices[-1]
    extract_plg.aperture_method.selected = 'Exact'
    extract_plg.wavelength_dependent = True
    extract_plg.function = 'Sum'
    # set so pixel scale factor != 1
    extract_plg.reference_spectral_value = 0.000001

    extract_plg.extract()

    data = cubeviz_helper.app.data_collection[-1].data
    values = [1]
    original_units = u.MJy / u.sr
    target_units = u.MJy

    spec = data.get_object(cls=Spectrum1D)
    viewer_equivs = viewer_flux_conversion_equivalencies(values, spec)
    value = flux_conversion_general(values, original_units,
                                    target_units, viewer_equivs,
                                    with_unit=False)

    # will be a uniform array since not wavelength dependent
    # so test first value in array
    assert np.allclose(value[0], 8e-11)

    # Change from Fnu to Flam (with values shape matching spectral axis)

    values = np.ones(3001)
    original_units = u.MJy
    target_units = u.erg / u.cm**2 / u.s / u.AA

    viewer_equivs = viewer_flux_conversion_equivalencies(values, spec)
    new_values = flux_conversion_general(values, original_units,
                                         target_units, viewer_equivs,
                                         with_unit=False)

    assert np.allclose(new_values,
                       (values * original_units)
                       .to_value(target_units,
                                 equivalencies=u.spectral_density(cube.spectral_axis)))

    # Change from Fnu to Flam (with a shape (2,) array of values indicating we
    # are probably converting the limits)

    values = [1, 2]
    original_units = u.MJy
    target_units = u.erg / u.cm**2 / u.s / u.AA

    viewer_equivs = viewer_flux_conversion_equivalencies(values, spec)
    new_values = flux_conversion_general(values, original_units,
                                         target_units, viewer_equivs,
                                         with_unit=False)

    # In this case we do a regular spectral density conversion, but using the
    # first value in the spectral axis for the equivalency
    assert np.allclose(new_values,
                       ([1, 2] * original_units)
                       .to_value(target_units,
                                 equivalencies=u.spectral_density(cube.spectral_axis[0])))


def test_all_plugins_have_description(cubeviz_helper, specviz_helper,
                                      mosviz_helper, imviz_helper,
                                      rampviz_helper, specviz2d_helper):
    """
    Test that all plugins for all configs have a plugin_description
    attribute, which controls what is displayed under the plugin title in the
    tray. Doesn't test what they are, just that they are not empty.
    """

    config_helpers = [cubeviz_helper, specviz_helper, mosviz_helper,
                      imviz_helper, rampviz_helper, specviz2d_helper]

    for config_helper in config_helpers:
        for item in config_helper.plugins:
            assert config_helper.plugins[item]._obj.plugin_description != ''
