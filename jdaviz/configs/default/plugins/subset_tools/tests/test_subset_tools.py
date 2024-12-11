import warnings
import pytest

import numpy as np
from astropy.nddata import NDData
import astropy.units as u
from regions import CirclePixelRegion, PixCoord
from specutils import SpectralRegion
from glue.core.roi import EllipticalROI, CircularROI, CircularAnnulusROI, RectangularROI
from glue.core.edit_subset_mode import ReplaceMode, OrMode
from numpy.testing import assert_allclose

from jdaviz.configs.default.plugins.subset_tools import utils
from jdaviz.core.region_translators import regions2roi


@pytest.mark.filterwarnings('ignore')
def test_plugin(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    p = specviz_helper.plugins['Subset Tools']

    # regression test for https://github.com/spacetelescope/jdaviz/issues/1693
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    p.import_region(SpectralRegion(6500 * unit, 7400 * unit))

    p.subset.selected = 'Create New'

    po = specviz_helper.plugins['Plot Options']
    po.layer = 'Subset 1'
    po.line_color = 'green'


def test_subset_definition_with_composite_subset(cubeviz_helper, spectrum1d_cube):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        cubeviz_helper.load_data(spectrum1d_cube)
    cubeviz_helper.app.get_tray_item_from_name('g-subset-tools')


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
    imviz_helper.plugins['Subset Tools'].import_region(roi_class(**roi_params))

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
    imviz_helper.link_data(align_by='wcs')
    assert plugin.display_sky_coordinates  # linking change should trigger change to True

    # apply original subset. transform sky coord of original subset to new pixels
    # using wcs of orientation layer (won't be the same as original pixels when pix linked)
    img_wcs = imviz_helper.app.data_collection['Default orientation'].coords
    new_pix_region = original_sky_region.to_pixel(img_wcs)
    new_roi = regions2roi(new_pix_region)
    imviz_helper.plugins['Subset Tools'].import_region(new_roi)

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


@pytest.mark.parametrize(
    ('spec_regions', 'mode', 'len_subsets', 'len_subregions'),
    [([SpectralRegion(5.772486091213352 * u.um, 6.052963676101135 * u.um),
       SpectralRegion(6.494371022809778 * u.um, 6.724270682553864 * u.um),
       SpectralRegion(7.004748267441649 * u.um, 7.3404016303483965 * u.um)], 'new', 3, 1),
     ([SpectralRegion(5.772486091213352 * u.um, 6.052963676101135 * u.um),
       SpectralRegion(6.494371022809778 * u.um, 6.724270682553864 * u.um),
       SpectralRegion(7.004748267441649 * u.um, 7.3404016303483965 * u.um)], 'replace', 1, 1),
     ((SpectralRegion(5.772486091213352 * u.um, 6.052963676101135 * u.um) +
       SpectralRegion(6.494371022809778 * u.um, 6.724270682553864 * u.um) +
       SpectralRegion(7.004748267441649 * u.um, 7.3404016303483965 * u.um)), 'or', 1, 3),
     ((SpectralRegion(5.772486091213352 * u.um, 6.052963676101135 * u.um) +
       SpectralRegion(5.8 * u.um, 5.9 * u.um) +
       SpectralRegion(6.494371022809778 * u.um, 6.724270682553864 * u.um) +
       SpectralRegion(7 * u.um, 7.2 * u.um)), ['new', 'andnot', 'or', 'or'], 1, 4),
     (SpectralRegion(5.8 * u.um, 5.9 * u.um), None, 1, 1)
     ]
)
def test_import_spectral_region(cubeviz_helper, spectrum1d_cube, spec_regions, mode, len_subsets,
                                len_subregions):
    cubeviz_helper.load_data(spectrum1d_cube)
    plg = cubeviz_helper.plugins['Subset Tools']
    plg.import_region(spec_regions, combination_mode=mode)
    subsets = cubeviz_helper.app.get_subsets()
    assert len(subsets) == len_subsets
    assert len(subsets['Subset 1']) == len_subregions
    assert cubeviz_helper.app.session.edit_subset_mode.mode == ReplaceMode


def test_import_spectral_regions_file(cubeviz_helper, spectrum1d_cube, tmp_path):
    cubeviz_helper.load_data(spectrum1d_cube)
    plg = cubeviz_helper.plugins['Subset Tools']
    s = SpectralRegion(5*u.um, 6*u.um)
    local_path = str(tmp_path / 'spectral_region.ecsv')
    s.write(local_path)
    plg.import_region(local_path)
    subsets = cubeviz_helper.app.get_subsets()
    assert len(subsets) == 1

    plg.combination_mode = 'or'
    plg.import_region(SpectralRegion(7 * u.um, 8 * u.um))

    subsets = cubeviz_helper.app.get_subsets()
    assert len(subsets['Subset 1']) == 2

    subset2 = (SpectralRegion(5.772486091213352 * u.um, 6.052963676101135 * u.um) +
               SpectralRegion(5.8 * u.um, 5.9 * u.um))
    plg.import_region(subset2, combination_mode=['new', 'andnot'])

    assert cubeviz_helper.app.session.edit_subset_mode.mode == OrMode

    with pytest.raises(ValueError, match='\'test\' not one of'):
        plg.combination_mode = 'test'


def test_get_regions(cubeviz_helper, spectrum1d_cube, imviz_helper):

    """Test Subset Tools.get regions."""

    cubeviz_helper.load_data(spectrum1d_cube)
    plg = cubeviz_helper.plugins['Subset Tools']

    # load one spectral region, which will become 'Subset 1'
    plg.import_region(SpectralRegion(1 * u.um, 2 * u.um))

    # load one spatial region, which will become 'Subset 2'
    spatial_reg = CirclePixelRegion(center=PixCoord(x=2, y=2), radius=2)
    plg.import_region(spatial_reg, combination_mode='new')

    # call get_regions, which by default for cubeviz will return both
    # spatial and spectral regions
    all_regions = plg.get_regions()
    assert len(all_regions) == 2

    # make sure filtering by subset label works
    only_s1 = plg.get_regions(list_of_subset_labels=['Subset 1'])
    assert len(only_s1) == 1
    assert only_s1['Subset 1']

    # now specify region type and check output
    spatial_regions = plg.get_regions(region_type='spatial')
    assert len(spatial_regions) == 1
    assert spatial_regions['Subset 2']
    spectral_regions = plg.get_regions(region_type='spectral')
    assert len(spectral_regions) == 1
    assert spectral_regions['Subset 1']

    # now test a composite spatial subset, make sure it is retrieved
    sr1 = CirclePixelRegion(center=PixCoord(x=2.5, y=2.5), radius=2)
    sr2 = CirclePixelRegion(center=PixCoord(x=2.5, y=3), radius=2)
    plg.import_region(sr1, combination_mode='new')
    plg.import_region(sr2, combination_mode='and')
    spatial_regions = plg.get_regions(region_type='spatial')
    assert spatial_regions['Subset 3']

    # test errors
    with pytest.raises(ValueError, match='No spectral subests in imviz.'):
        imviz_helper.plugins['Subset Tools'].get_regions('spectral')
    with pytest.raises(ValueError, match="`region_type` must be 'spectral', 'spatial', or None for any."):  # noqa E501
        plg.get_regions(region_type='fail')


@pytest.mark.xfail(reason='Unskip once issue XXXX is resolved.')
def test_get_regions_composite(cubeviz_helper, spectrum1d_cube):
    """
    If you apply a circular subset mask to a circular subset to make a
    composite subset, and they aren't exactly aligned at the center to form a
    circular annulus, obtaining the region through ``get_interactive_regions``
    (now deprecated, replaced with get_regions in Subset Tools) fails.
    However, you can retrieve the compound subset as a ``region`` with
    ``app.get_subsets``. This test ensures that a region is returned through
    both ``app.get_subsets`` and ``get_regions``.
    """
    cubeviz_helper.load_data(spectrum1d_cube)
    plg = cubeviz_helper.plugins['Subset Tools']

    # For some reason, Subset 2 disappears after the third subset is applied
    # when loaded this way. Uncomment to replace _apply_interactive_region once
    # JDAT-5014 is resolved
    # plg.import_region(CirclePixelRegion(center=PixCoord(x=96.0, y=96.0),
    #                                     radius=45.0), combination_mode='new')
    # plg.import_region(CirclePixelRegion(center=PixCoord(x=95.0, y=95.0),
    #                                     radius=25.0), combination_mode='new')

    # apply two circular subsets
    cubeviz_helper._apply_interactive_region('bqplot:truecircle', (51, 51), (141, 141))
    cubeviz_helper._apply_interactive_region('bqplot:truecircle', (70, 70), (120, 120))

    # apply composite subset created from two existing circular subsets
    subset_groups = cubeviz_helper.app.data_collection.subset_groups
    new_subset = subset_groups[0].subset_state & ~subset_groups[1].subset_state
    cubeviz_helper.default_viewer._obj.apply_subset_state(new_subset)

    # make sure Subset 3, the composite subset, is retrieved.
    regions = plg.get_regions()
    ss_labels = ['Subset 1', 'Subset 2', 'Subset 3']
    assert np.all([regions[ss] for ss in ss_labels])

    # make sure the same regions are returned by app.get_subsets
    get_subsets = cubeviz_helper.app.get_subsets()
    assert np.all([get_subsets[ss][0]['region'] == regions[ss] for ss in ss_labels])
