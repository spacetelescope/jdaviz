import operator
import warnings

import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.nddata import NDData
from glue.core.edit_subset_mode import ReplaceMode, OrMode, NewMode
from glue.core.roi import EllipticalROI, CircularROI, CircularAnnulusROI, RectangularROI
from numpy.testing import assert_allclose
from regions import (CircleAnnulusPixelRegion, CirclePixelRegion,
                     CircleSkyRegion, CompoundPixelRegion, CompoundSkyRegion,
                     PixCoord)
from specutils import SpectralRegion

from jdaviz.configs.default.plugins.subset_tools import utils
from jdaviz.core.region_translators import regions2roi


def test_plugin(specviz_helper, spectrum1d):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
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
    # as a CompoundRegion (since operator is &)
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


def test_get_regions_composite(imviz_helper):
    """
    Test the behavior of retrieving composite subsets as regions
    using subset_tools.get_regions
    """
    a = np.ones((200, 200))
    imviz_helper.load_data(a, data_label="test")
    plg = imviz_helper.plugins['Subset Tools']

    # apply two (not concentric) circular subsets
    plg.import_region(CirclePixelRegion(center=PixCoord(x=96.0, y=96.0),
                                        radius=45.0), combination_mode='new')
    plg.import_region(CirclePixelRegion(center=PixCoord(x=100.0, y=100.0),
                                        radius=25.0), combination_mode='new')

    # create a composite subset created from these circular subsets
    # that are applied with remove/and not to subtract the smaller from the larger
    imviz_helper.app.session.edit_subset_mode._mode = NewMode
    subset_groups = imviz_helper.app.data_collection.subset_groups
    new_subset = subset_groups[0].subset_state & ~subset_groups[1].subset_state
    imviz_helper.default_viewer._obj.apply_subset_state(new_subset)

    # call get_regions and make sure Subset 3, the composite subset, is retrieved,
    # but as a list of tuples of  individual subsets and their combination modes,
    # since they were created with &~ and do not form an exact circular annulus
    regions = plg.get_regions()
    assert sorted(regions) == ["Subset 1", "Subset 2", "Subset 3"]
    assert len(regions['Subset 3']) == 2
    assert isinstance(regions['Subset 3'][0][0], CirclePixelRegion)
    assert regions['Subset 3'][0][1] == ''  # first operator should be ''
    assert isinstance(regions['Subset 3'][1][0], CirclePixelRegion)
    assert regions['Subset 3'][1][1] == 'AndNotState'

    # make sure the same regions are returned by app.get_subsets
    get_subsets = imviz_helper.app.get_subsets()
    assert sorted(get_subsets) == ["Subset 1", "Subset 2", "Subset 3"]

    # Now, create two concentric circular subsets and combine them to form a circular annulus.
    plg.import_region(CirclePixelRegion(center=PixCoord(x=95.0, y=95.0),
                                        radius=45.0), combination_mode='new')
    plg.import_region(CirclePixelRegion(center=PixCoord(x=95.0, y=95.0),
                                        radius=25.0), combination_mode='new')
    imviz_helper.app.session.edit_subset_mode._mode = NewMode
    subset_groups = imviz_helper.app.data_collection.subset_groups
    new_subset = subset_groups[3].subset_state & ~subset_groups[4].subset_state
    imviz_helper.default_viewer._obj.apply_subset_state(new_subset)

    # now, when get_regions is called, the combined subset should be represented as a
    # CircleAnnulusPixelRegion rather than two circlular subsets
    regions = plg.get_regions()
    assert isinstance(regions['Subset 6'], CircleAnnulusPixelRegion)

    # If and/or/xor are used to create composite subsets, they can be
    # represented as CompoundRegions.
    for sub, op in [('7', operator.and_), ('8', operator.or_), ('9', operator.xor)]:
        imviz_helper.app.session.edit_subset_mode._mode = NewMode
        new_subset = op(subset_groups[3].subset_state, subset_groups[4].subset_state)
        imviz_helper.default_viewer._obj.apply_subset_state(new_subset)
        regions = plg.get_regions()
        assert isinstance(regions[f'Subset {sub}'], CompoundPixelRegion)


def test_get_regions_composite_wcs_linked(imviz_helper, image_2d_wcs):
    data = NDData(np.ones((128, 128)) * u.nJy, wcs=image_2d_wcs)
    imviz_helper.load_data(data)

    imviz_helper.plugins['Orientation'].align_by = 'WCS'

    st = imviz_helper.plugins['Subset Tools']

    sr1 = CircleSkyRegion(center=SkyCoord(ra=337.5058778*u.deg,
                          dec=-20.808486*u.deg), radius=0.008*u.deg)
    sr2 = CircleSkyRegion(center=SkyCoord(ra=337.51*u.deg, dec=-20.81*u.deg),
                          radius=0.007*u.deg)
    st.import_region(sr1, combination_mode='new')
    st.import_region(sr2, combination_mode='and')

    # composite subset should be a sky region, and combined to a compound region
    regs = st.get_regions()

    cr = regs['Subset 1']
    assert isinstance(cr, CompoundSkyRegion)
    assert_allclose(cr.region1.center.ra.deg, sr1.center.ra.deg)
    assert_allclose(cr.region2.center.ra.deg, sr2.center.ra.deg)
    assert cr.operator == operator.and_


@pytest.mark.skip(reason="Unskip after JDAT-5186.")
def test_get_composite_sky_region_remove(imviz_helper, image_2d_wcs):
    """
    Test to ensure bug fixed by JDAT-5186 is fixed, where get_subsets
    for compoisute subset applied with 'remove' when WCS linked was not
    correctly retrieving the second subset.
    """
    data = NDData(np.ones((128, 128)) * u.nJy, wcs=image_2d_wcs)
    imviz_helper.load_data(data)

    imviz_helper.plugins['Orientation'].align_by = 'WCS'

    st = imviz_helper.plugins['Subset Tools']

    sr1 = CircleSkyRegion(center=SkyCoord(ra=337.5058778*u.deg,
                          dec=-20.808486*u.deg), radius=0.008*u.deg)
    sr2 = CircleSkyRegion(center=SkyCoord(ra=337.51*u.deg, dec=-20.81*u.deg),
                          radius=0.007*u.deg)
    st.import_region(sr1, combination_mode='new')
    st.import_region(sr2, combination_mode='andnot')

    # app.get_subsets
    ss = imviz_helper.app.get_subsets(include_sky_region=True)

    # composite region should be returned as 2 sky regions
    assert isinstance(ss['Subset 1'][0]['sky_region'], CircleSkyRegion)
    assert isinstance(ss['Subset 1'][1]['sky_region'], CircleSkyRegion)

    # now make sure Subset Tools get_regions agrees and both sky regions
    # are returned for Subset 1
    regs = st.get_regions()
    assert isinstance(regs['Subset 1'][0], CircleSkyRegion)
    assert isinstance(regs['Subset 1'][1], CircleSkyRegion)


def test_check_valid_subset_label(imviz_helper):

    # imviz instance with some data
    data = NDData(np.ones((50, 50)) * u.nJy)
    imviz_helper.load_data(data)

    st = imviz_helper.plugins["Subset Tools"]

    # apply three subsets, with their default names of `Subset 1`, `Subset 2`, and `Subset 3`
    st.import_region(CircularROI(20, 20, 10))
    st.subset = "Create New"
    st.import_region(CircularROI(25, 25, 10))
    st.subset = "Create New"
    st.import_region(CircularROI(30, 30, 10))

    # we should not be able to rename or add a subset named 'Subset 1'.
    # Make sure this warns and returns accordingly.
    with pytest.raises(ValueError, match="Cannot rename subset to name of an existing subset"):
        st.rename_selected("Subset 1")

    with pytest.raises(ValueError, match="The pattern 'Subset N' is reserved"):
        st.rename_selected("Subset 5")


def test_rename_subset(cubeviz_helper, spectrum1d_cube):

    cubeviz_helper.load_data(spectrum1d_cube)
    plg = cubeviz_helper.plugins['Subset Tools']

    spatial_reg = CirclePixelRegion(center=PixCoord(x=2, y=2), radius=2)
    plg.import_region(spatial_reg, combination_mode='new')
    spatial_reg = CirclePixelRegion(center=PixCoord(x=4, y=4), radius=1)
    plg.import_region(spatial_reg, combination_mode='new')

    plg.rename_subset("Subset 1", "Test Rename")

    assert plg.subset.choices == ['Create New', 'Test Rename', 'Subset 2']
    assert cubeviz_helper.app.data_collection[-1].label == "Spectrum (Test Rename, sum)"

    plg.rename_selected("Second Test")
    assert plg.subset.choices == ['Create New', 'Test Rename', 'Second Test']

    with pytest.raises(ValueError, match="No subset named BadLabel to rename"):
        plg.rename_subset("BadLabel", "Failure")


def test_update_subset(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    plg = cubeviz_helper.plugins['Subset Tools']

    spatial_reg = CirclePixelRegion(center=PixCoord(x=2, y=2), radius=2)
    plg.import_region(spatial_reg, combination_mode='new')
    spatial_reg = CirclePixelRegion(center=PixCoord(x=4, y=4), radius=1)
    plg.import_region(spatial_reg, combination_mode='and')

    subset_def = plg.update_subset('Subset 1')
    print(subset_def)
    assert isinstance(subset_def, dict)
    assert len(subset_def) == 2

    with pytest.raises(ValueError, match='subset has more than one subregion'):
        plg.update_subset('Subset 1', xc=1)

    with pytest.raises(ValueError, match='not an attribute of the specified subset/subregion.'):
        plg.update_subset('Subset 1', subregion=0, notanattribute=1)

    plg.update_subset('Subset 1', subregion=0, xc=3, yc=1, radius=1)

    # Check xc
    assert plg._obj.subset_definitions[0][1]['value'] == 3
    # Check yc
    assert plg._obj.subset_definitions[0][2]['value'] == 1
    # Check radius
    assert plg._obj.subset_definitions[0][3]['value'] == 1
