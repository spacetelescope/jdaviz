import pytest
from astropy.utils.exceptions import AstropyUserWarning
from specutils import Spectrum1D


def test_linking_after_spectral_smooth(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    dc = app.data_collection
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')
    spec_viewer = cubeviz_helper.app.get_viewer('spectrum-viewer')

    assert len(dc) == 1

    gs = cubeviz_helper.plugins['Gaussian Smooth']._obj
    gs.dataset_selected = 'test[FLUX]'
    gs.mode_selected = 'Spectral'
    gs.stddev = 3.2
    gs.add_to_viewer_selected = 'None'
    assert gs.results_label == 'spectral-smooth stddev-3.2'
    gs.vue_apply()
    # when not showing the results, the label will remain the same,
    # so there should be an overwrite warning
    assert gs.results_label_overwrite is True
    gs.add_to_viewer_selected = 'spectrum-viewer'
    gs.vue_apply()
    # but since we're overwriting, add_to_viewer_selected is ignored (and hidden in the UI)
    # so will still be hidden
    assert len(gs.dataset_items) == 1
    # by removing the data entry, the overwrite will no longer apply
    app.remove_data_from_viewer('spectrum-viewer', 'spectral-smooth stddev-3.2')
    app.data_collection.remove(app.data_collection['spectral-smooth stddev-3.2'])

    gs.add_to_viewer_selected = 'spectrum-viewer'
    gs.vue_apply()
    # since we now plotted the results, the dataset should be fixed,
    # but the dataset dropdown contains multiple choices, so the dataset
    # itself is prepended to the default label, and there is no longer
    # an overwrite warning.
    assert len(gs.dataset_items) == 2
    assert gs.dataset_selected == 'test[FLUX]'
    assert gs.results_label == 'test[FLUX] spectral-smooth stddev-3.2'
    assert gs.results_label_overwrite is False

    assert len(dc) == 2
    assert dc[1].label == 'spectral-smooth stddev-3.2'
    assert len(dc.external_links) == 3

    # Link cube 3D x, y, z to plugin 3D x, y, z

    # Link 2:
    # Pixel Axis 0 [z] from cube.pixel_component_ids[0]
    # Pixel Axis 0 [z] from plugin.pixel_component_ids[0]
    assert dc.external_links[0].cids1[0] == dc[0].pixel_component_ids[0]
    assert dc.external_links[0].cids2[0] == dc[-1].pixel_component_ids[0]

    # Link 3:
    # Pixel Axis 1 [y] from cube.pixel_component_ids[1]
    # Pixel Axis 1 [y] from plugin.pixel_component_ids[1]
    assert dc.external_links[1].cids1[0] == dc[0].pixel_component_ids[1]
    assert dc.external_links[1].cids2[0] == dc[-1].pixel_component_ids[1]

    # Link 4:
    # Pixel Axis 2 [x] from cube.pixel_component_ids[2]
    # Pixel Axis 2 [x] from plugin.pixel_component_ids[2]
    assert dc.external_links[2].cids1[0] == dc[0].pixel_component_ids[2]
    assert dc.external_links[2].cids2[0] == dc[-1].pixel_component_ids[2]

    # Mouseover should automatically jump from one spectrum
    # to another, depending on which one is closer.

    spec_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 4.633e-7, 'y': 60}})
    assert spec_viewer.label_mouseover.pixel == 'x=01.0'
    assert spec_viewer.label_mouseover.world_label_prefix == 'Wave'
    assert spec_viewer.label_mouseover.world_ra == '4.62360e-07'
    assert spec_viewer.label_mouseover.world_dec == 'm'
    assert spec_viewer.label_mouseover.world_label_prefix_2 == 'Flux'
    assert spec_viewer.label_mouseover.world_ra_deg == '9.20000e+01'
    assert spec_viewer.label_mouseover.world_dec_deg == 'Jy'
    assert spec_viewer.label_mouseover.icon == 'a'

    spec_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 4.633e-7, 'y': 20}})
    assert spec_viewer.label_mouseover.pixel == 'x=01.0'
    assert spec_viewer.label_mouseover.world_label_prefix == 'Wave'
    assert spec_viewer.label_mouseover.world_ra == '4.62360e-07'
    assert spec_viewer.label_mouseover.world_dec == 'm'
    assert spec_viewer.label_mouseover.world_label_prefix_2 == 'Flux'
    assert spec_viewer.label_mouseover.world_ra_deg == '1.47943e+01'
    assert spec_viewer.label_mouseover.world_dec_deg == 'Jy'
    assert spec_viewer.label_mouseover.icon == 'b'

    # Check mouseover behavior when we hide everything.
    for lyr in spec_viewer.layers:
        lyr.visible = False

    spec_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 4.633e-7, 'y': 60}})
    assert spec_viewer.label_mouseover.pixel == ''
    assert spec_viewer.label_mouseover.world_label_prefix == '\xa0'
    assert spec_viewer.label_mouseover.world_ra == ''
    assert spec_viewer.label_mouseover.world_dec == ''
    assert spec_viewer.label_mouseover.world_label_prefix_2 == '\xa0'
    assert spec_viewer.label_mouseover.world_ra_deg == ''
    assert spec_viewer.label_mouseover.world_dec_deg == ''
    assert spec_viewer.label_mouseover.icon == ''


def test_spatial_convolution(cubeviz_helper, spectrum1d_cube):
    dc = cubeviz_helper.app.data_collection
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    gs = cubeviz_helper.plugins['Gaussian Smooth']._obj
    gs.dataset_selected = 'test[FLUX]'
    gs.mode_selected = 'Spatial'
    gs.stddev = 3
    assert gs.results_label == 'spatial-smooth stddev-3.0'
    with pytest.warns(
            AstropyUserWarning,
            match='The following attributes were set on the data object, but will be ignored'):
        gs.vue_apply()

    assert len(dc) == 2
    assert dc[1].label == "spatial-smooth stddev-3.0"
    assert dc[1].shape == (2, 4, 2)  # specutils moved spectral axis to last
    assert (dc["spatial-smooth stddev-3.0"].get_object(cls=Spectrum1D, statistic=None).shape
            == (2, 4, 2))


def test_spectrum1d_smooth(specviz_helper, spectrum1d):
    dc = specviz_helper.app.data_collection
    specviz_helper.load_data(spectrum1d, data_label='test')
    spec_viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    gs = specviz_helper.plugins['Gaussian Smooth']._obj
    gs.dataset_selected = 'test'
    gs.mode_selected = 'Spectral'
    gs.stddev = 10
    gs.vue_apply()

    assert len(dc) == 2
    assert dc[1].label == 'smooth stddev-10.0'

    # Mouseover should automatically jump from one spectrum
    # to another, depending on which one is closer.

    spec_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 6400, 'y': 120}})
    assert spec_viewer.label_mouseover.pixel == 'x=02.0'
    assert spec_viewer.label_mouseover.world_label_prefix == 'Wave'
    assert spec_viewer.label_mouseover.world_ra == '6.44444e+03'
    assert spec_viewer.label_mouseover.world_dec == 'Angstrom'
    assert spec_viewer.label_mouseover.world_label_prefix_2 == 'Flux'
    assert spec_viewer.label_mouseover.world_ra_deg == '1.35366e+01'
    assert spec_viewer.label_mouseover.world_dec_deg == 'Jy'
    assert spec_viewer.label_mouseover.icon == 'a'

    spec_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 6400, 'y': 5}})
    assert spec_viewer.label_mouseover.pixel == 'x=02.0'
    assert spec_viewer.label_mouseover.world_label_prefix == 'Wave'
    assert spec_viewer.label_mouseover.world_ra == '6.44444e+03'
    assert spec_viewer.label_mouseover.world_dec == 'Angstrom'
    assert spec_viewer.label_mouseover.world_label_prefix_2 == 'Flux'
    assert spec_viewer.label_mouseover.world_ra_deg == '5.34688e+00'
    assert spec_viewer.label_mouseover.world_dec_deg == 'Jy'
    assert spec_viewer.label_mouseover.icon == 'b'

    # Out-of-bounds should lock to closest edge value.
    spec_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 5500, 'y': 120}})
    assert spec_viewer.label_mouseover.pixel == 'x=00.0'
    assert spec_viewer.label_mouseover.world_label_prefix == 'Wave'
    assert spec_viewer.label_mouseover.world_ra == '6.00000e+03'
    assert spec_viewer.label_mouseover.world_dec == 'Angstrom'
    assert spec_viewer.label_mouseover.world_label_prefix_2 == 'Flux'
    assert spec_viewer.label_mouseover.world_ra_deg == '1.24967e+01'
    assert spec_viewer.label_mouseover.world_dec_deg == 'Jy'
    assert spec_viewer.label_mouseover.icon == 'a'
