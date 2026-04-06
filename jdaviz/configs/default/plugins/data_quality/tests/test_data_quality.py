import warnings
import pytest

from astropy.utils import minversion
import gwcs
import numpy as np
from stdatamodels.jwst.datamodels.dqflags import pixel as pixel_jwst
from glue.core.subset import RectangularROI

from jdaviz.configs.imviz.plugins.parsers import HAS_ROMAN_DATAMODELS
from jdaviz.configs.default.plugins.data_quality.dq_utils import (
    load_flag_map, write_flag_map
)
from jdaviz.utils import cached_uri

GWCS_LT_0_26_2 = not minversion(gwcs, "0.26.2.dev")


@pytest.mark.parametrize(
    "mission_or_instrument, flag, name,",
    [['jwst', 26, 'OPEN'],
     ['roman', 26, 'RESERVED_5'],
     ['jwst', 15, 'TELEGRAPH'],
     ['roman', 15, 'TELEGRAPH']]
)
def test_flag_map_utils(mission_or_instrument, flag, name):
    flag_map = load_flag_map(mission_or_instrument)
    assert flag_map[flag]['name'] == name


def test_load_write_load(tmp_path):
    # load the JWST flag map
    flag_map = load_flag_map('jwst')

    # write out the flag map to a temporary CSV file
    path = tmp_path / 'test_flag_map.csv'
    write_flag_map(flag_map, path)

    # load that temporary CSV file back in
    reloaded_flag_map = load_flag_map(path=path)

    # confirm all values round-trip successfully:
    for flag, orig_value in flag_map.items():
        assert orig_value == reloaded_flag_map[flag]


def test_jwst_against_stdatamodels():
    # compare our flag map against the flag map dictionary in `stdatamodels`:
    flag_map_loaded = load_flag_map('jwst')

    flag_map_expected = {
        int(np.log2(flag)): {'name': name}
        for name, flag in pixel_jwst.items() if flag > 0
    }

    # check no keys are missing in either flag map:
    assert len(set(flag_map_loaded.keys()) - set(flag_map_expected.keys())) == 0

    for flag in flag_map_expected:
        assert flag_map_loaded[flag]['name'] == flag_map_expected[flag]['name']


@pytest.mark.skipif(not HAS_ROMAN_DATAMODELS, reason="roman_datamodels is not installed")
def test_roman_against_rdm():
    # compare our flag map against the flag map dictionary in `roman_datamodels`:
    from roman_datamodels.dqflags import pixel as pixel_roman

    flag_map_loaded = load_flag_map('roman')

    flag_map_expected = {
        int(np.log2(p.value)): {'name': p.name}
        for p in pixel_roman if p.value > 0
    }

    # check no keys are missing in either flag map:
    assert len(set(flag_map_loaded.keys()) - set(flag_map_expected.keys())) == 0

    for flag in flag_map_expected:
        assert flag_map_loaded[flag]['name'] == flag_map_expected[flag]['name']


@pytest.mark.remote_data
@pytest.mark.parametrize('helper_name', ['imviz_helper', 'deconfigged_helper'])
def test_data_quality_plugin(helper_name, request):
    helper = request.getfixturevalue(helper_name)
    uri = "mast:JWST/product/jw01895001004_07101_00001_nrca3_cal.fits"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        helper.load(cached_uri(uri), extension=('SCI', 'DQ'), format='Image',
                    cache=True)

    assert len(helper._app.data_collection) == 2

    # this assumption is made in the DQ plugin (for now)
    assert helper._app.data_collection[-1].label.endswith('[DQ,1]')

    dq_plugin = helper.plugins['Data Quality']._obj

    # sci+dq layers are correctly identified
    expected_science_data, expected_dq_data = helper._app.data_collection
    assert dq_plugin.science_layer_selected == expected_science_data.label
    assert dq_plugin.dq_layer_selected == expected_dq_data.label

    # JWST data product identified as such:
    assert dq_plugin.flag_map_selected == 'JWST'

    # check flag 0 is a bad pixel in the JWST flag map:
    flag_map_selected = dq_plugin.flag_map_definitions_selected
    assert flag_map_selected[0]['name'] == 'DO_NOT_USE'
    assert flag_map_selected[0]['description'] == 'Bad pixel. Do not use.'

    # get the image viewer (name depends on config)
    viewer_name = 'Image' if helper_name == 'deconfigged_helper' else 'imviz-0'
    viewer = helper._app.get_viewer(viewer_name)

    # check default dq opacity is a fraction of sci data:
    sci_alpha = viewer.layers[0].state.alpha
    dq_alpha = viewer.layers[1].state.alpha
    assert dq_alpha == sci_alpha * dq_plugin.dq_layer_opacity

    plot_opts = helper.plugins['Plot Options']._obj

    # only the sci data appears in Plot Options:
    assert len(plot_opts.layer_items) == 1

    # check changes to sci opacity affect dq opacity
    new_sci_opacity = 0.5
    plot_opts.image_opacity_value = new_sci_opacity
    dq_alpha = viewer.layers[1].state.alpha
    assert dq_alpha == new_sci_opacity * dq_plugin.dq_layer_opacity

    # check that mouseover shows dq values on bad pixels (flag == 0):
    label_mouseover = helper._coords_info
    label_mouseover._viewer_mouse_event(viewer,
                                        {'event': 'mousemove', 'domain': {'x': 1366, 'y': 708}})

    # DQ features are labeled in the first line:
    label_mouseover_text = label_mouseover.as_text()[0]

    # bad pixels with flag == 0 have flux == NaN
    expected_flux_label = '+nan MJy / sr'
    assert expected_flux_label in label_mouseover_text

    # check that the decomposed DQ flag is at the end of the flux label's line:
    flux_label_idx = label_mouseover_text.index(expected_flux_label)
    associated_dq_layer = dq_plugin.get_dq_layers(viewer)[0]
    dq_data = associated_dq_layer.layer.get_data(associated_dq_layer.state.attribute)
    dq_val = dq_data[708, 1366]
    assert label_mouseover_text[flux_label_idx + len(expected_flux_label) + 1:] == f'(DQ: {dq_val:.0f})'  # noqa: E501

    # check that a flagged pixel that is not marked with the bit 0 has a flux in mouseover label:
    label_mouseover._viewer_mouse_event(viewer,
                                        {'event': 'mousemove', 'domain': {'x': 1371, 'y': 715}})
    label_mouseover_text = label_mouseover.as_text()[0]
    dq_val = dq_data[715, 1371]
    assert label_mouseover_text.split('+')[1].endswith(f'(DQ: {dq_val:.0f})')

    # check that a pixel without a DQ flag has no DQ mouseover label:
    label_mouseover._viewer_mouse_event(viewer,
                                        {'event': 'mousemove', 'domain': {'x': 1361, 'y': 684}})
    dq_val = dq_data[684, 1361]
    assert np.isnan(dq_val)
    label_mouseover_text = label_mouseover.as_text()[0]
    assert 'DQ' not in label_mouseover_text

    # set a bit filter, then clear it:
    assert len(dq_plugin.flags_filter) == 0
    dq_plugin.flags_filter = [0, 1]
    dq_plugin.vue_clear_flags_filter({})
    assert len(dq_plugin.flags_filter) == 0

    # hide all:
    dq_plugin.vue_hide_all_flags({})
    assert not any([flag['show'] for flag in dq_plugin.decoded_flags])

    # now show all:
    dq_plugin.vue_show_all_flags({})
    assert all([flag['show'] for flag in dq_plugin.decoded_flags])


@pytest.mark.remote_data
def test_data_quality_plugin_hst_wfc3(imviz_helper):

    # load HST/WFC3-UVIS observations:
    uri = "mast:HST/product/hst_17183_02_wfc3_uvis_g280_iexr02mt_flt.fits"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        imviz_helper.load_data(cached_uri(uri), cache=True, ext=('SCI', 'DQ'))

    assert len(imviz_helper._app.data_collection) == 2

    dq_plugin = imviz_helper.plugins['Data Quality']._obj

    # mission+instrument+detector identified:
    assert dq_plugin.flag_map_selected == 'HST/WFC3-UVIS'

    flag_map_selected = dq_plugin.flag_map_definitions_selected
    assert flag_map_selected[0]['description'] == 'Reed Solomon decoding error'


@pytest.mark.remote_data
def test_data_quality_plugin_hst_acs(imviz_helper):
    # load HST/ACS observations:
    uri = "mast:HST/product/hst_16968_01_acs_wfc_f606w_jezz01l3_flt.fits"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        imviz_helper.load_data(cached_uri(uri), cache=True, ext=('SCI', 'DQ'))

    assert len(imviz_helper._app.data_collection) == 2

    dq_plugin = imviz_helper.plugins['Data Quality']._obj

    # mission+instrument identified:
    assert dq_plugin.flag_map_selected == 'HST/ACS'

    flag_map_selected = dq_plugin.flag_map_definitions_selected
    assert (
        flag_map_selected[0]['description'] ==
        'Reed-Solomon decoding error; e.g. data lost during compression.'
    )


@pytest.mark.remote_data
@pytest.mark.parametrize('helper_name', ['cubeviz_helper', 'deconfigged_helper'])
def test_cubeviz_dq_plugin_and_layer_visibility_bug(helper_name, request):
    """
    This test covers two things (combined to reduce the number of remote data
    tests). First, it has coverage for a (now fixed) bug in the Data Quality
    plugin that attempted to apply array compositing logic to spatial subsets.
    Second, it tests basic functionality of the data quality plugin in Cubeviz.
    """
    helper = request.getfixturevalue(helper_name)

    uri = "mast:JWST/product/jw02732-c1001_t004_miri_ch1-short_s3d.fits"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        helper.load(cached_uri(uri), cache=True, format='3D Spectrum')

    dq_plugin = helper.plugins['Data Quality']._obj

    # in the data collection there should be flux, unc, extracted spectrum,
    # and the DQ cube for a total of 4 items
    assert len(helper.app.data_collection) == 4

    # this assumption is made in the DQ plugin (for now)
    assert helper.app.data_collection[-1].label.endswith('[DQ]')

    # sci+dq layers are correctly identified
    expected_science_data = helper.app.data_collection[0]
    expected_dq_data = helper.app.data_collection[-1]
    assert dq_plugin.science_layer_selected == expected_science_data.label
    assert dq_plugin.dq_layer_selected == expected_dq_data.label

    # JWST data product identified as such:
    assert dq_plugin.flag_map_selected == 'JWST'

    # check flag 0 is a bad pixel in the JWST flag map:
    flag_map_selected = dq_plugin.flag_map_definitions_selected
    assert flag_map_selected[0]['name'] == 'DO_NOT_USE'
    assert flag_map_selected[0]['description'] == 'Bad pixel. Do not use.'

    plot_opts = helper.plugins['Plot Options']._obj

    # only the sci data appears in Plot Options when the flux viewer is selected
    if helper_name == 'cubeviz_helper':
        assert plot_opts.viewer_selected == 'flux-viewer'
    else:
        plot_opts.viewer_selected = '3D Spectrum'
    assert len(plot_opts.layer_items) == 1

    # check changes to sci opacity affect dq opacity
    new_sci_opacity = 0.5
    plot_opts.image_opacity_value = new_sci_opacity
    viewer_name = '3D Spectrum' if helper_name == 'deconfigged_helper' else 'flux-viewer'
    viewer = helper.viewers[viewer_name]._obj.glue_viewer
    dq_alpha = viewer.layers[1].state.alpha
    assert dq_alpha == new_sci_opacity * dq_plugin.dq_layer_opacity

    # check that mouseover shows dq values on flagged pixels
    label_mouseover = helper._coords_info
    label_mouseover._viewer_mouse_event(viewer,
                                        {'event': 'mousemove', 'domain': {'x': 40, 'y': 34}})

    # DQ features are labeled in the first line:
    label_mouseover_text = label_mouseover.as_text()[0]
    expected_flux_label = '+nan MJy / sr'
    assert expected_flux_label in label_mouseover_text

    # check that the decomposed DQ flag is at the end of the flux label's line:
    flux_label_idx = label_mouseover_text.index(expected_flux_label)
    associated_dq_layer = dq_plugin.get_dq_layers(viewer)[0]
    dq_data = associated_dq_layer.layer.get_data(associated_dq_layer.state.attribute)
    dq_val = dq_data[34, 40][0]
    assert label_mouseover_text[flux_label_idx + len(expected_flux_label) + 1:] == f'(DQ: {dq_val:.0f})'  # noqa: E501

    # Regression test for layer visibility bug (cubeviz-specific)
    if helper_name == 'cubeviz_helper':
        # create a moment map:
        mm = helper.plugins['Moment Maps']
        mm.n_moment = 1
        mm.reference_wavelength = 6
        mm._obj.add_to_viewer_selected = 'uncert-viewer'
        mm.calculate_moment()

        # add the moment map to the flux viewer
        dc = helper.app.data_collection
        viewer = helper.app.get_viewer('flux-viewer')
        viewer.add_data(dc[-1])

        # create a spatial subset in the flux-viewer
        roi = RectangularROI(22, 27, 22, 30)
        helper.plugins['Subset Tools'].import_region(roi)

        # toggle layer visibility, this used to trigger an AttributeError:
        helper.app.set_data_visibility('flux-viewer', dc[-1].label)
        helper.app.set_data_visibility('flux-viewer', dc[0].label)
