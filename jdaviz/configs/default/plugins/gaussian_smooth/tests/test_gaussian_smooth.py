import numpy as np
import pytest
from astropy.utils.exceptions import AstropyUserWarning
from specutils import Spectrum1D


def test_linking_after_spectral_smooth(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    dc = app.data_collection
    data_label = 'test'
    cubeviz_helper.load_data(spectrum1d_cube, data_label=data_label)
    spec_viewer = cubeviz_helper.app.get_viewer('spectrum-viewer')

    assert len(dc) == 1

    gs = cubeviz_helper.plugins['Gaussian Smooth']._obj
    gs.dataset_selected = f'{data_label}[FLUX]'
    gs.mode_selected = 'Spectral'
    gs.stddev = 3.2
    gs.add_to_viewer_selected = 'None'
    assert gs.results_label == f'{data_label}[FLUX] spectral-smooth stddev-3.2'
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
    app.remove_data_from_viewer('spectrum-viewer', f'{data_label}[FLUX] spectral-smooth stddev-3.2')
    app.data_collection.remove(
        app.data_collection[f'{data_label}[FLUX] spectral-smooth stddev-3.2'])

    gs.add_to_viewer_selected = 'spectrum-viewer'
    gs.vue_apply()

    # FOR HISTORICAL CONTEXT:
    # The data label used to be prepended to the results_label ONLY if there were multiple
    # smoothed spectra. As of PR#1973, POs requested the data label to always be present.
    # As a result, label will overwrite here
    assert len(gs.dataset_items) == 1
    assert gs.dataset_selected == f'{data_label}[FLUX]'
    assert gs.results_label == f'{data_label}[FLUX] spectral-smooth stddev-3.2'
    assert gs.results_label_overwrite is True

    assert len(dc) == 2
    assert dc[1].label == f'{data_label}[FLUX] spectral-smooth stddev-3.2'
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

    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 4.6236e-7, 'y': 60}})
    assert label_mouseover.as_text() == ('Cursor 4.62360e-07, 6.00000e+01',
                                         'Wave 4.62360e-07 m (1 pix)',
                                         'Flux 9.20000e+01 Jy')
    assert label_mouseover.icon == 'a'

    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 4.6236e-7, 'y': 20}})
    assert label_mouseover.as_text() == ('Cursor 4.62360e-07, 2.00000e+01',
                                         'Wave 4.62360e-07 m (1 pix)',
                                         'Flux 1.47943e+01 Jy')
    assert label_mouseover.icon == 'b'

    # Check mouseover behavior when we hide everything.
    for lyr in spec_viewer.layers:
        lyr.visible = False

    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 4.6236e-7, 'y': 60}})
    assert label_mouseover.as_text() == ('Cursor 4.62360e-07, 6.00000e+01', '', '')
    assert label_mouseover.icon == 'mdi-cursor-default'


def test_spatial_convolution(cubeviz_helper, spectrum1d_cube):
    data_label = 'test'
    dc = cubeviz_helper.app.data_collection
    cubeviz_helper.load_data(spectrum1d_cube, data_label=data_label)

    gs = cubeviz_helper.plugins['Gaussian Smooth']._obj
    gs.dataset_selected = f'{data_label}[FLUX]'
    gs.mode_selected = 'Spatial'
    gs.stddev = 3
    assert gs.results_label == f'{data_label}[FLUX] spatial-smooth stddev-3.0'
    with pytest.warns(
            AstropyUserWarning,
            match='The following attributes were set on the data object, but will be ignored'):
        gs.vue_apply()

    assert len(dc) == 2
    assert dc[1].label == f'{data_label}[FLUX] spatial-smooth stddev-3.0'
    assert dc[1].shape == (2, 4, 2)  # specutils moved spectral axis to last
    assert (dc[f'{data_label}[FLUX] spatial-smooth stddev-3.0'].get_object(cls=Spectrum1D,
                                                                           statistic=None).shape
            == (2, 4, 2))


def test_specviz_smooth(specviz_helper, spectrum1d):
    data_label = 'test'
    dc = specviz_helper.app.data_collection
    specviz_helper.load_data(spectrum1d, data_label=data_label)
    spec_viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    gs = specviz_helper.plugins['Gaussian Smooth']._obj
    gs.dataset_selected = data_label
    gs.mode_selected = 'Spectral'
    gs.stddev = 10
    gs.vue_apply()

    assert len(dc) == 2
    assert dc[1].label == f'{data_label} smooth stddev-10.0'

    # Mouseover should automatically jump from one spectrum
    # to another, depending on which one is closer.

    label_mouseover = specviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 6400, 'y': 120}})
    assert label_mouseover.as_text() == ('Cursor 6.40000e+03, 1.20000e+02',
                                         'Wave 6.44444e+03 Angstrom (2 pix)',
                                         'Flux 1.35366e+01 Jy')
    assert label_mouseover.icon == 'a'

    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 6400, 'y': 5}})
    assert label_mouseover.as_text() == ('Cursor 6.40000e+03, 5.00000e+00',
                                         'Wave 6.44444e+03 Angstrom (2 pix)',
                                         'Flux 5.34688e+00 Jy')
    assert label_mouseover.icon == 'b'

    # Out-of-bounds shows only cursor info.
    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 5500, 'y': 120}})
    assert label_mouseover.as_text() == ('Cursor 5.50000e+03, 1.20000e+02', '', '')
    assert label_mouseover.icon == 'mdi-cursor-default'


def test_specviz2d_smooth(specviz2d_helper, spectrum2d):
    data_label = 'test'
    dc = specviz2d_helper.app.data_collection
    specviz2d_helper.load_data(spectrum_2d=spectrum2d, spectrum_2d_label=data_label)

    gs_plugin = specviz2d_helper.plugins['Gaussian Smooth']

    # The Autocollapsed spectrum is given the label of "Spectrum 1D by default"
    smooth_source_dataset = "Spectrum 1D"
    gs_plugin.dataset = smooth_source_dataset
    test_stddev_level = 10.0
    gs_plugin.stddev = test_stddev_level
    smoothed_spectrum = gs_plugin.smooth(add_data=True)

    assert len(dc) == 3
    assert dc[2].label == f'{smooth_source_dataset} smooth stddev-{test_stddev_level}'
    np.testing.assert_allclose(smoothed_spectrum.spectral_axis.value,
                               spectrum2d.spectral_axis.value)

    # Ensure all marks were created properly (i.e. not in their initialized state)
    # [0,1] is the default (initialization) value for the marks
    marks = specviz2d_helper.app.get_viewer('spectrum-viewer').native_marks
    assert len(marks) == 2

    gp_mark = marks[-1]
    np.testing.assert_allclose(gp_mark.x, smoothed_spectrum.spectral_axis.value)
    np.testing.assert_allclose(gp_mark.y, smoothed_spectrum.flux.value)
