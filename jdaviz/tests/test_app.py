import pytest
from copy import deepcopy

import numpy as np
from astropy import units as u
from astropy.wcs import WCS
from specutils import Spectrum
from ipywidgets.widgets import widget_serialization

from jdaviz import Specviz, Specviz2d
from jdaviz.core.config import get_configuration
from jdaviz.app import Application
from jdaviz.configs.default.plugins.gaussian_smooth.gaussian_smooth import GaussianSmooth
from jdaviz.core.unit_conversion_utils import (flux_conversion_general,
                                               viewer_flux_conversion_equivalencies)


# This applies to all viz but testing with Imviz should be enough.
def test_viewer_calling_app(imviz_helper):
    viewer = imviz_helper.default_viewer._obj.glue_viewer
    assert viewer.session.jdaviz_app is imviz_helper.app


def test_get_tray_item_from_name():
    app = Application(configuration='default')
    plg = app.get_tray_item_from_name('g-gaussian-smooth')
    assert isinstance(plg, GaussianSmooth)

    with pytest.raises(KeyError, match='imviz-compass not found'):
        app.get_tray_item_from_name('imviz-compass')


@pytest.mark.xfail(reason="hardcoded config logic during deconfigging process")
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
                                                          'plot': 'spectrum-1d-viewer',
                                                          'reference': 'h'},
                                                         {'name': 'K',
                                                          'plot': 'spectrum-1d-viewer',
                                                          'reference': 'k'}]}]}]}

    class Customviz(Specviz):
        _default_configuration = config
        _default_spectrum_viewer_reference_name = 'h'

    viz = Customviz()
    assert viz.app.get_viewer_reference_names() == ['h', 'k']

    viz.load_data(spectrum1d, data_label='example label')
    with pytest.raises(KeyError):
        viz.datasets["non-existent label"]


@pytest.mark.parametrize(('input_data', 'input_format'), [
    ('image_hdu_wcs', 'Image'),
    ('spectrum1d', '1D Spectrum'),
    ('spectrum2d', '2D Spectrum'),
    ('spectrum1d_cube', '3D Spectrum'),
])
def test_duplicate_data_labels(deconfigged_helper, input_data, input_format, request):
    input_data = request.getfixturevalue(input_data)

    # Currently, 3D spectra can't have duplicates (only one flux cube allowed at a time)
    # Remove this block when multiple cube support is added
    if input_format == '3D Spectrum':
        deconfigged_helper.load(input_data, format=input_format, data_label="test")
        with pytest.raises(ValueError,
                           match="Only one 3D spectrum.*flux cube.*can be loaded at a time"):
            deconfigged_helper.load(input_data, format=input_format, data_label="test")
        return

    # Test duplicate auto-generated labels
    deconfigged_helper.load(input_data, format=input_format)
    deconfigged_helper.load(input_data, format=input_format)
    dc = deconfigged_helper.app.data_collection

    expected_label_base = input_format
    if input_format == 'Image':
        expected_label_base = 'Image[SCI,1]'

    assert any([dc_entry.label == expected_label_base for dc_entry in dc])
    assert any([dc_entry.label == f'{expected_label_base} (1)' for dc_entry in dc])

    # Test overwrite when using custom labels
    deconfigged_helper.load(input_data, format=input_format, data_label="test")
    deconfigged_helper.load(input_data, format=input_format, data_label="test")

    test_labels = [dc_entry.label == 'test' for dc_entry in dc]
    assert any(test_labels)
    assert sum(test_labels) == 1
    assert 'test (1)' not in dc

    deconfigged_helper.load(input_data, format=input_format, data_label=expected_label_base)
    deconfigged_helper.load(input_data, format=input_format, data_label="test_1")

    # Test second attempt at overwrite using custom label
    # that matches the expected auto-generated label
    assert f'{expected_label_base} (2)' not in dc
    assert any([dc_entry.label == 'test_1' for dc_entry in dc])


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


def test_edge_cases(deconfigged_helper, spectrum1d):
    data_labels = ['111111',
                   'aaaaa',
                   '///(#$@)',
                   'two  spaces  repeating',
                   'word42word42word  two  spaces']

    dc = deconfigged_helper.app.data_collection

    for dl in data_labels:
        deconfigged_helper.load(spectrum1d, data_label=dl)
        assert dl in dc


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

    with pytest.raises(ValueError):
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
    cube = Spectrum(flux=flux * (u.MJy / u.sr), wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    # this can be removed once spectra pass through cube spectral extraction
    extract_plg = cubeviz_helper.plugins['3D Spectral Extraction']

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

    spec = data.get_object(cls=Spectrum)
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


@pytest.mark.parametrize(('server_is_remote', 'remote_enable_importers'),
                         [(None, None),
                          (False, False),
                          (True, False),
                          (False, True),
                          (True, True)])
def test_remote_server_settings_config(server_is_remote, remote_enable_importers):
    config = get_configuration('specviz2d')
    if server_is_remote is not None:
        config['settings']['server_is_remote'] = server_is_remote
        config['settings']['remote_enable_importers'] = remote_enable_importers

    specviz2d_app = Application(config)
    specviz2d_helper = Specviz2d(specviz2d_app)
    settings = specviz2d_helper.app.state.settings

    if server_is_remote is None:
        # Defaults
        assert settings['server_is_remote'] is False
        server_is_remote = False
        assert settings['remote_enable_importers'] is True
    else:
        # Explicit settings
        assert settings['server_is_remote'] == server_is_remote
        assert settings['remote_enable_importers'] == remote_enable_importers

    # Get the loader items and check their widget properties
    loader_items = specviz2d_helper.app.state.loader_items

    for loader_item in loader_items:
        widget_model_id = loader_item['widget']
        loader_widget = widget_serialization['from_json'](widget_model_id, None)

        # Check that the server_is_remote traitlet is properly synced
        assert hasattr(loader_widget, 'server_is_remote')
        assert loader_widget.server_is_remote == server_is_remote


@pytest.mark.parametrize('server_is_remote', [False, True])
def test_remote_server_settings_deconfigged(deconfigged_helper, server_is_remote):
    settings = deconfigged_helper.app.state.settings
    # Defaults
    assert settings['server_is_remote'] is False
    assert settings['remote_enable_importers'] is True
    # Create a new dict and reassign to trigger callbacks
    new_settings = settings.copy()
    new_settings['server_is_remote'] = server_is_remote
    deconfigged_helper.app.state.settings = new_settings

    # Get the loader items and check their widget properties
    loader_items = deconfigged_helper.app.state.loader_items

    for loader_item in loader_items:
        widget_model_id = loader_item['widget']
        loader_widget = widget_serialization['from_json'](widget_model_id, None)

        # Check that the server_is_remote traitlet is properly synced
        assert hasattr(loader_widget, 'server_is_remote')
        assert loader_widget.server_is_remote == server_is_remote


# Pick a smattering of fixture/data types
@pytest.mark.parametrize(('fixture_to_load', 'fixture_format'),
                         [('image_hdu_wcs', 'Image'),
                          ('image_nddata_wcs', 'Image'),
                          ('spectrum1d', '1D Spectrum'),
                          ('spectrum2d', '2D Spectrum')])
def test_update_existing_data_in_dc(deconfigged_helper,
                                    fixture_to_load, fixture_format, request):
    # Check that existing_data_in_dc is empty to start
    assert len(deconfigged_helper.app.existing_data_in_dc) == 0

    deconfigged_helper.load(request.getfixturevalue(fixture_to_load), format=fixture_format)
    # Check that existing_data_in_dc was updated upon adding data
    assert len(deconfigged_helper.app.existing_data_in_dc) > 0

    # Use this data for testing
    dc_data = deconfigged_helper.app.data_collection[0]

    # Check that the update goes through
    test_data_in_dc = deepcopy(deconfigged_helper.app.existing_data_in_dc)
    # Remove some data
    deconfigged_helper.app._update_existing_data_in_dc(dc_data, data_added=False)
    assert test_data_in_dc != deconfigged_helper.app.existing_data_in_dc

    # Add it back
    deconfigged_helper.app._update_existing_data_in_dc(dc_data, data_added=True)

    test_data_in_dc = deepcopy(deconfigged_helper.app.existing_data_in_dc)
    # If this key is present, an update will occur so check that
    # nothing happens when it is not present.
    dh = dc_data.data.meta.pop('_data_hash')
    deconfigged_helper.app._update_existing_data_in_dc(dc_data, data_added=True)
    assert test_data_in_dc == deconfigged_helper.app.existing_data_in_dc

    # Check that removing the data via data collection updates existing_data_in_dc
    len_before = len(deconfigged_helper.app.existing_data_in_dc)
    deconfigged_helper.app.data_collection[0].meta['_data_hash'] = dh
    deconfigged_helper.app.data_item_remove(dc_data.label)
    assert len(deconfigged_helper.app.existing_data_in_dc) != len_before
    assert dh not in deconfigged_helper.app.existing_data_in_dc


def test_add_custom_loader_file(deconfigged_helper, tmp_path):
    """Test _add_custom_loader with a file resolver."""
    # Create a temporary FITS file
    filepath = tmp_path / "test_data.fits"
    filepath.touch()

    # Add a custom file loader
    loader = deconfigged_helper.app._add_custom_loader('file', str(filepath), name='test_file')

    assert repr(loader) == '<test_file API>'
    assert 'test_file' in deconfigged_helper.app._jdaviz_helper.loaders

    # Check that the loader was added to loader_items
    loader_names = [item['name'] for item in deconfigged_helper.app.state.loader_items]
    assert 'test_file' in loader_names


def test_add_custom_loader_object(deconfigged_helper, spectrum1d):
    """Test _add_custom_loader with an object resolver."""
    from astropy.table import Table

    # Create a simple table object
    test_table = Table({'col1': [1, 2, 3], 'col2': [4, 5, 6]})

    # Add a custom object loader
    loader = deconfigged_helper.app._add_custom_loader('object', test_table, name='my_table')

    assert repr(loader) == '<my_table API>'
    assert 'my_table' in deconfigged_helper.app._jdaviz_helper.loaders

    # Check that requires_api_support is set correctly for object resolver
    loader_items = deconfigged_helper.app.state.loader_items
    my_table_item = [item for item in loader_items if item['name'] == 'my_table'][0]
    assert my_table_item['requires_api_support'] is True


def test_add_custom_loader_url(deconfigged_helper):
    """Test _add_custom_loader with a URL resolver."""
    # Use a simple test URL (it doesn't need to be valid for the loader creation)
    test_url = 'https://example.com/test_data.fits'

    # Add a custom URL loader
    loader = deconfigged_helper.app._add_custom_loader('url', test_url, name='remote_file')

    assert repr(loader) == '<remote_file API>'
    assert 'remote_file' in deconfigged_helper.app._jdaviz_helper.loaders


def test_add_custom_loader_invalid_resolver(deconfigged_helper):
    """Test _add_custom_loader with an invalid resolver type."""
    with pytest.raises(ValueError, match="Unknown resolver type 'invalid'"):
        deconfigged_helper.app._add_custom_loader('invalid', 'some_input', name='test')


def test_add_custom_loader_unique_names(deconfigged_helper, tmp_path):
    """Test that _add_custom_loader raises an error when duplicate names exist."""
    # Create temporary files
    filepath1 = tmp_path / "data.fits"
    filepath1.touch()
    filepath2 = tmp_path / "data2.fits"
    filepath2.touch()

    # Add first loader with name 'data'
    loader1 = deconfigged_helper.app._add_custom_loader('file', str(filepath1), name='data')
    assert repr(loader1) == '<data API>'

    # Try to add second loader with the same name - should raise error
    with pytest.raises(ValueError, match="Loader name must be unique. A loader with the name 'data' already exists."):  # noqa
        deconfigged_helper.app._add_custom_loader('file', str(filepath2), name='data')


def test_add_custom_loader_open_in_tray(deconfigged_helper, tmp_path):
    """Test _add_custom_loader with open_in_tray option."""
    filepath = tmp_path / "test.fits"
    filepath.touch()

    # Add a custom file loader with open_in_tray=True
    loader = deconfigged_helper.app._add_custom_loader(
        'file', str(filepath), name='test', open_in_tray=True
    )

    # The loader should be returned and the name should match
    assert repr(loader) == '<test API>'
