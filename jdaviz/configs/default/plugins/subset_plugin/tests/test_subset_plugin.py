import warnings
import pytest

import numpy as np
from astropy.nddata import NDData
from glue.core.roi import EllipticalROI, CircularROI, CircularAnnulusROI, RectangularROI, XRangeROI
from numpy.testing import assert_allclose

from jdaviz.configs.default.plugins.subset_plugin import utils
from jdaviz.core.region_translators import regions2roi


@pytest.mark.filterwarnings('ignore')
def test_plugin(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    p = specviz_helper.plugins['Subset Tools']

    # regression test for https://github.com/spacetelescope/jdaviz/issues/1693
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    sv.apply_roi(XRangeROI(6500, 7400))

    p._obj.subset_select.selected = 'Create New'

    po = specviz_helper.plugins['Plot Options']
    po.layer = 'Subset 1'
    po.line_color = 'green'


def test_subset_definition_with_composite_subset(cubeviz_helper, spectrum1d_cube):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        cubeviz_helper.load_data(spectrum1d_cube)
    cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')


circle_subset_info = {'xc': {'pixel_name': 'X Center (pixels)', 'wcs_name':
                             'RA Center (degrees)', 'initial_value': 5,
                             'final_value': 6},
                      'yc': {'pixel_name': 'Y Center (pixels)', 'wcs_name':
                             'Dec Center (degrees)', 'initial_value': 5,
                             'final_value': 6},
                      'radius': {'pixel_name': 'Radius (pixels)', 'wcs_name':
                                 'Radius (degrees)', 'initial_value': 2,
                                 'final_value': 3}}
elliptical_subset_info = {'xc': {'pixel_name': 'X Center (pixels)', 'wcs_name':
                                 'RA Center (degrees)', 'initial_value': 5.,
                                 'final_value': 6.},
                          'yc': {'pixel_name': 'Y Center (pixels)', 'wcs_name':
                                 'Dec Center (degrees)', 'initial_value': 5.,
                                 'final_value': 6.},
                          'radius_x': {'pixel_name': 'X Radius (pixels)', 'wcs_name':
                                       'RA Radius (degrees)', 'initial_value': 2.,
                                       'final_value': 3.},
                          'radius_y': {'pixel_name': 'Y Radius (pixels)', 'wcs_name':
                                       'Dec Radius (degrees)', 'initial_value': 5.,
                                       'final_value': 6.},
                          'theta': {'pixel_name': 'Angle', 'wcs_name':
                                    'Angle', 'initial_value': 0.,
                                    'final_value': 45.}}
circ_annulus_subset_info = {'xc': {'pixel_name': 'X Center (pixels)', 'wcs_name':
                                   'RA Center (degrees)', 'initial_value': 5.,
                                   'final_value': 6.},
                            'yc': {'pixel_name': 'Y Center (pixels)', 'wcs_name':
                                   'Dec Center (degrees)', 'initial_value': 5.,
                                   'final_value': 6.},
                            'inner_radius': {'pixel_name': 'Inner Radius (pixels)', 'wcs_name':
                                             'Inner Radius (degrees)', 'initial_value': 2.,
                                             'final_value': 3.},
                            'outer_radius': {'pixel_name': 'Outer Radius (pixels)', 'wcs_name':
                                             'Outer Radius (degrees)', 'initial_value': 5.,
                                             'final_value': 6.}}
rectangular_subset_info = {'xmin': {'pixel_name': 'Xmin (pixels)', 'wcs_name':
                                    'RA min (degrees)', 'initial_value': 5.,
                                    'final_value': 6.},
                           'xmax': {'pixel_name': 'Xmax (pixels)', 'wcs_name':
                                    'RA max (degrees)', 'initial_value': 6.,
                                    'final_value': 7.},
                           'ymin': {'pixel_name': 'Ymin (pixels)', 'wcs_name':
                                    'Dec min (degrees)', 'initial_value': 2.,
                                    'final_value': 3.},
                           'ymax': {'pixel_name': 'Ymax (pixels)', 'wcs_name':
                                    'Dec max (degrees)', 'initial_value': 5.,
                                    'final_value': 6.}}


@pytest.mark.parametrize("roi_class, subset_info", [(CircularROI, circle_subset_info),
                                                    (EllipticalROI, elliptical_subset_info),
                                                    (CircularAnnulusROI, circ_annulus_subset_info),
                                                    (RectangularROI, rectangular_subset_info)])
def test_circle_recenter_linking(roi_class, subset_info, imviz_helper, image_2d_wcs):

    arr = np.ones((10, 10))
    ndd = NDData(arr, wcs=image_2d_wcs)
    imviz_helper.load_data(ndd, data_label='dataset1')
    imviz_helper.load_data(ndd, data_label='dataset2')

    # apply subset
    roi_params = {key: subset_info[key]['initial_value'] for key in subset_info}
    imviz_helper.app.get_viewer('imviz-0').apply_roi(roi_class(**roi_params))

    # get plugin and check that attribute tracking link type is set properly
    plugin = imviz_helper.plugins['Subset Tools']._obj
    assert not plugin.display_sky_coordinates

    # get initial subset definitions from ROI applied
    subset_defs = plugin.subset_definitions

    # check that the subset definitions, which control what is displayed in the UI, are correct
    for i, attr in enumerate(subset_info):
        assert subset_defs[0][i+1]['name'] == subset_info[attr]['pixel_name']
        assert subset_defs[0][i+1]['value'] == subset_info[attr]['initial_value']

    # get original subset location as a sky region for use later
    original_subs = imviz_helper.app.get_subsets(include_sky_region=True)
    original_sky_region = original_subs['Subset 1'][0]['sky_region']

    # move subset (subset state is what is modified in UI)
    for attr in subset_info:
        plugin._set_value_in_subset_definition(0, subset_info[attr]['pixel_name'],
                                               attr, subset_info[attr]['final_value'])

    # update subset to apply these changes
    plugin.vue_update_subset()
    subset_defs = plugin.subset_definitions

    # and check that it is changed after vue_update_subset runs
    for i, attr in enumerate(subset_info):
        assert subset_defs[0][i+1]['name'] == subset_info[attr]['pixel_name']
        assert subset_defs[0][i+1]['value'] == subset_info[attr]['final_value']

    # get updated subset location as a sky region, we need this later
    updated_sky_region = imviz_helper.app.get_subsets(include_sky_region=True)
    updated_sky_region = updated_sky_region['Subset 1'][0]['sky_region']

    # remove subsets and change link type to wcs
    dc = imviz_helper.app.data_collection
    dc.remove_subset_group(dc.subset_groups[0])
    imviz_helper.link_data(link_type='wcs')
    assert plugin.display_sky_coordinates  # linking change should trigger change to True

    # apply original subset. transform sky coord of original subset to new pixels
    # using wcs of orientation layer (won't be the same as original pixels when pix linked)
    img_wcs = imviz_helper.app.data_collection['Default orientation'].coords
    new_pix_region = original_sky_region.to_pixel(img_wcs)
    new_roi = regions2roi(new_pix_region)
    imviz_helper.app.get_viewer('imviz-0').apply_roi(new_roi)

    # get subset definitions again, which should now be in sky coordinates
    subset_defs = plugin.subset_definitions

    # check that the subset definitions, which control what is displayed in the UI,
    # are correct and match original sky region generated when we were first pix linked
    true_values_orig = utils._sky_region_to_subset_def(original_sky_region)

    for i, attr in enumerate(subset_info):
        assert subset_defs[0][i+1]['name'] == subset_info[attr]['wcs_name']
        assert_allclose(subset_defs[0][i+1]['value'], true_values_orig[i]['value'])

    true_values_final = utils._sky_region_to_subset_def(updated_sky_region)

    for i, attr in enumerate(subset_info):
        plugin._set_value_in_subset_definition(0, subset_info[attr]['wcs_name'],
                                               attr, true_values_final[i]['value'])
    # update subset
    plugin.vue_update_subset()

    subset_defs = plugin.subset_definitions
    for i, attr in enumerate(subset_info):
        assert subset_defs[0][i+1]['name'] == subset_info[attr]['wcs_name']
        assert_allclose(subset_defs[0][i+1]['value'], true_values_final[i]['value'])
