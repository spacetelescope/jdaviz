import warnings

import pytest
import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.tests.helper import assert_quantity_allclose
from astropy.utils.data import get_pkg_data_filename
from numpy.testing import assert_allclose, assert_array_equal
from photutils.aperture import (ApertureStats, CircularAperture, EllipticalAperture,
                                RectangularAperture, EllipticalAnnulus)
from photutils.datasets import make_4gaussians_image
from regions import (CircleAnnulusPixelRegion, CirclePixelRegion, EllipsePixelRegion,
                     RectanglePixelRegion, PixCoord)

from jdaviz.configs.imviz.plugins.aper_phot_simple.aper_phot_simple import (
    _curve_of_growth, _radial_profile)
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS, BaseImviz_WCS_NoWCS
from jdaviz.core.custom_units_and_equivs import PIX2


class TestSimpleAperPhot(BaseImviz_WCS_WCS):
    def test_plugin_wcs_dithered(self):
        self.imviz.link_data(align_by='wcs')  # They are dithered by 1 pixel on X

        reg = CirclePixelRegion(center=PixCoord(x=4.5, y=4.5), radius=4.5).to_sky(self.wcs_1)
        self.imviz.plugins['Subset Tools'].import_region(reg)

        phot_plugin = self.imviz.plugins['Aperture Photometry']

        # Model fitting is already tested in astropy.
        # Here, we enable it just to make sure it does not crash.
        phot_plugin.fit_radial_profile = True

        # Make sure invalid Data/Subset selection does not crash plugin.
        with pytest.raises(ValueError):
            phot_plugin.dataset.selected = 'no_such_data'
        with pytest.raises(ValueError):
            # will raise an error and revert to first entry
            phot_plugin.aperture.selected = 'no_such_subset'
        assert phot_plugin.aperture.selected == ''
        phot_plugin.aperture.selected = phot_plugin.aperture.labels[0]
        assert_allclose(phot_plugin.background_value, 0)

        phot_plugin.dataset.selected = 'has_wcs_1[SCI,1]'
        phot_plugin.aperture.selected = phot_plugin.aperture.labels[0]
        with pytest.raises(ValueError):
            phot_plugin.background.selected = 'no_such_subset'
        assert phot_plugin.background.selected == 'Manual'
        assert_allclose(phot_plugin.background_value, 0)

        # Perform photometry on both images using same Subset.
        phot_plugin.dataset.selected = 'has_wcs_1[SCI,1]'
        phot_plugin.aperture.selected = 'Subset 1'
        assert phot_plugin.dataset.selected_dc_item is not None
        phot_plugin._obj.vue_do_aper_phot()
        tbl = phot_plugin.export_table()
        assert len(tbl) == 1

        phot_plugin.dataset.selected = 'has_wcs_2[SCI,1]'
        phot_plugin.current_plot_type = 'Radial Profile (Raw)'
        assert phot_plugin.dataset.selected_dc_item is not None
        assert phot_plugin.aperture.selected_spatial_region is not None
        assert phot_plugin.background.labels == ['Manual', 'Subset 1']
        assert_allclose(phot_plugin.background_value, 0)
        assert_allclose(phot_plugin.counts_factor, 0)
        assert_allclose(phot_plugin.pixel_area, 0)
        assert_allclose(phot_plugin.flux_scaling, 0)
        phot_plugin._obj.vue_do_aper_phot()
        tbl = phot_plugin.export_table()
        assert len(tbl) == 2
        assert phot_plugin._obj.plot_available
        assert len(phot_plugin.plot._obj.layers['profile'].layer.data['x']) > 0

        # Check photometry results.
        assert tbl.colnames == [
            'id', 'xcenter', 'ycenter', 'sky_center', 'background', 'sum',
            'sum_aper_area', 'pixarea_tot', 'aperture_sum_counts', 'aperture_sum_counts_err',
            'counts_fac', 'aperture_sum_mag', 'flux_scaling', 'min', 'max', 'mean', 'median',
            'mode', 'std', 'mad_std', 'var', 'biweight_location', 'biweight_midvariance',
            'fwhm', 'semimajor_sigma', 'semiminor_sigma', 'orientation', 'eccentricity',
            'data_label', 'subset_label', 'timestamp']
        assert_array_equal(tbl['id'], [1, 2])
        assert_allclose(tbl['background'], 0)
        assert_quantity_allclose(tbl['sum_aper_area'], [63.617251, 62.22684693104279] * PIX2, rtol=1e-4)  # noqa
        assert_array_equal(tbl['pixarea_tot'], None)
        assert_array_equal(tbl['aperture_sum_counts'], None)
        assert_array_equal(tbl['aperture_sum_counts_err'], None)
        assert_array_equal(tbl['counts_fac'], None)
        assert_array_equal(tbl['aperture_sum_mag'], None)
        assert_array_equal(tbl['flux_scaling'], None)
        assert_allclose(tbl['min'], 1)
        assert_allclose(tbl['max'], 1)
        assert_allclose(tbl['mean'], 1)
        assert_allclose(tbl['median'], 1)
        assert_allclose(tbl['mode'], 1)
        assert_allclose(tbl['std'], 0)
        assert_allclose(tbl['mad_std'], 0)
        assert_allclose(tbl['var'], 0)
        assert_allclose(tbl['biweight_location'], 1)
        assert_allclose(tbl['biweight_midvariance'], 0)
        assert_quantity_allclose(tbl['fwhm'], 5.15018758 * u.pix)
        assert_quantity_allclose(tbl['semimajor_sigma'], 2.18708329 * u.pix)
        assert_quantity_allclose(tbl['semiminor_sigma'], 2.18708329 * u.pix)
        assert_quantity_allclose(tbl['orientation'], 0 * u.deg)
        assert_quantity_allclose(tbl['eccentricity'], 0)
        assert_array_equal(tbl['data_label'], ['has_wcs_1[SCI,1]', 'has_wcs_2[SCI,1]'])
        assert_array_equal(tbl['subset_label'], ['Subset 1', 'Subset 1'])
        assert tbl['timestamp'].scale == 'utc'

        # Sky is the same but xcenter different due to dithering.
        # The aperture sum is different too because mask is a little off limit in second image.
        assert_quantity_allclose(tbl['xcenter'], [4.5, 5.5] * u.pix, rtol=1e-4)
        assert_quantity_allclose(tbl['ycenter'], 4.5 * u.pix, rtol=1e-4)
        sky = tbl['sky_center']
        assert_allclose(sky.ra.deg, 337.518943)
        assert_allclose(sky.dec.deg, -20.832083)
        assert_allclose(tbl['sum'], [63.617251, 62.22684693104279], rtol=1e-4)

        # Make sure it also works on an ellipse subset.
        reg = EllipsePixelRegion(center=PixCoord(x=4.5, y=2.0), width=9.0, height=4.0).to_sky(self.wcs_1)  # noqa: E501
        self.imviz.plugins['Subset Tools'].combination_mode = 'new'
        self.imviz.plugins['Subset Tools'].import_region(reg)

        phot_plugin.dataset.selected = 'has_wcs_1[SCI,1]'
        phot_plugin.aperture.selected = 'Subset 2'
        phot_plugin.current_plot_type = 'Radial Profile'
        phot_plugin._obj.vue_do_aper_phot()
        tbl = phot_plugin.export_table()
        assert len(tbl) == 3  # New result is appended
        assert tbl[-1]['id'] == 3
        assert_quantity_allclose(tbl[-1]['xcenter'], 4.5 * u.pix, rtol=1e-4)
        assert_quantity_allclose(tbl[-1]['ycenter'], 2 * u.pix, rtol=1e-4)
        sky = tbl[-1]['sky_center']
        assert_allclose(sky.ra.deg, 337.51894336144454, rtol=1e-4)
        assert_allclose(sky.dec.deg, -20.832777499255897, rtol=1e-4)
        assert_quantity_allclose(tbl[-1]['sum_aper_area'], 28.274334 * PIX2, rtol=1e-4)
        assert_allclose(tbl[-1]['sum'], 28.274334, rtol=1e-4)
        assert_allclose(tbl[-1]['mean'], 1, rtol=1e-4)
        assert tbl[-1]['data_label'] == 'has_wcs_1[SCI,1]'
        assert tbl[-1]['subset_label'] == 'Subset 2'

        # Make sure it also works on a rectangle subset.
        # We also subtract off background from itself here.
        reg = RectanglePixelRegion(center=PixCoord(x=4.5, y=4.5), width=9, height=9).to_sky(self.wcs_1)  # noqa: E501
        self.imviz.plugins['Subset Tools'].combination_mode = 'new'
        self.imviz.plugins['Subset Tools'].import_region(reg)

        phot_plugin.dataset.selected = 'has_wcs_1[SCI,1]'
        phot_plugin.aperture.selected = 'Subset 3'
        phot_plugin.background.selected = 'Subset 3'
        assert_allclose(phot_plugin.background_value, 1)
        phot_plugin._obj.vue_do_aper_phot()
        tbl = phot_plugin.export_table()
        assert len(tbl) == 4  # New result is appended
        assert tbl[-1]['id'] == 4
        assert_quantity_allclose(tbl[-1]['xcenter'], 4.5 * u.pix)
        assert_quantity_allclose(tbl[-1]['ycenter'], 4.5 * u.pix)
        sky = tbl[-1]['sky_center']
        assert_allclose(sky.ra.deg, 337.51894336144454, rtol=1e-4)
        assert_allclose(sky.dec.deg, -20.832083, rtol=1e-4)
        assert_quantity_allclose(tbl[-1]['sum_aper_area'], 81 * PIX2)
        assert_allclose(tbl[-1]['sum'], 0)
        assert_allclose(tbl[-1]['mean'], 0)
        assert tbl[-1]['data_label'] == 'has_wcs_1[SCI,1]'
        assert tbl[-1]['subset_label'] == 'Subset 3'

        # Make sure background auto-updates.
        phot_plugin.background.selected = 'Manual'
        assert_allclose(phot_plugin.background_value, 1)  # Keeps last value
        phot_plugin.background.selected = 'Subset 1'
        assert_allclose(phot_plugin.background_value, 1)

        hdu3 = fits.ImageHDU(np.ones((10, 10)) + 1, name='SCI')
        hdu3.header.update(self.wcs_2.to_header())
        self.imviz.load_data(hdu3, data_label='twos')
        phot_plugin.dataset.selected = 'twos[SCI,1]'
        assert_allclose(phot_plugin.background_value, 2)  # Recalculate based on new Data

        # Curve of growth
        phot_plugin.current_plot_type = 'Curve of Growth'
        phot_plugin._obj.vue_do_aper_phot()
        assert phot_plugin.plot._obj.figure.title == 'Curve of growth from aperture center'

    def test_batch_unpack(self):
        phot_plugin = self.imviz.plugins['Aperture Photometry']

        # NOTE: these input values are not currently validated, so it does not matter that the
        # datasets and subsets do not exist with these names (if that changes, this test will
        # need to be udpated accordingly)
        unpacked = phot_plugin.unpack_batch_options(dataset=['image1', 'image2'],
                                                    aperture=['Subset 1', 'Subset 2'],
                                                    background=['Subset 3'],
                                                    flux_scaling=3)
        assert unpacked == [{'aperture': 'Subset 1',
                             'dataset': 'image1',
                             'background': 'Subset 3',
                             'flux_scaling': 3},
                            {'aperture': 'Subset 2',
                             'dataset': 'image1',
                             'background': 'Subset 3',
                             'flux_scaling': 3},
                            {'aperture': 'Subset 1',
                             'dataset': 'image2',
                             'background': 'Subset 3',
                             'flux_scaling': 3},
                            {'aperture': 'Subset 2',
                             'dataset': 'image2',
                             'background': 'Subset 3',
                             'flux_scaling': 3}]

    def test_batch_phot(self):
        self.imviz.link_data(align_by='wcs')  # They are dithered by 1 pixel on X
        self.imviz.plugins['Subset Tools'].import_region(
            CirclePixelRegion(center=PixCoord(x=4.5, y=4.5), radius=4.5)
        )  # Draw a circle

        phot_plugin = self.imviz.plugins['Aperture Photometry']
        assert phot_plugin.dataset.choices == ['has_wcs_1[SCI,1]', 'has_wcs_2[SCI,1]']
        assert phot_plugin.aperture.choices == ['Subset 1']

        phot_plugin.aperture.selected = 'Subset 1'
        phot_plugin.calculate_batch_photometry([{'dataset': 'has_wcs_1[SCI,1]', 'aperture': 'Subset 1'},  # noqa
                                                {'dataset': 'has_wcs_2[SCI,1]'}])

        assert len(phot_plugin.table._obj) == 2

        with pytest.raises(RuntimeError):
            phot_plugin.calculate_batch_photometry([{'dataset': 'has_wcs_1[SCI,1]', 'aperture': 'DNE'},  # noqa
                                                    {'dataset': 'has_wcs_2[SCI,1]', 'aperture': 'Subset 1'}])  # noqa

        # second entry above should have been successful, resulting in one addition to the results
        assert len(phot_plugin.table._obj) == 3

        # now run through the UI directly
        phot_plugin.multiselect = True
        phot_plugin.dataset.select_all()
        phot_plugin.aperture.select_none()
        assert len(phot_plugin.unpack_batch_options()) == 0
        phot_plugin._obj.vue_do_aper_phot()

        assert len(phot_plugin.table._obj) == 3
        phot_plugin.aperture.select_all()
        assert len(phot_plugin.unpack_batch_options()) == 2
        phot_plugin._obj.vue_do_aper_phot()
        assert len(phot_plugin.table._obj) == 5


class TestSimpleAperPhot_NoWCS(BaseImviz_WCS_NoWCS):
    def test_plugin_no_wcs(self):
        # Most things already tested above, so not re-tested here.
        self.imviz.plugins['Subset Tools'].import_region(
            CirclePixelRegion(center=PixCoord(x=4.5, y=4.5), radius=4.5)
        )  # Draw a circle
        phot_plugin = self.imviz.plugins['Aperture Photometry']

        phot_plugin.dataset.selected = 'has_wcs[SCI,1]'
        phot_plugin.aperture.selected = 'Subset 1'
        phot_plugin._obj.vue_do_aper_phot()
        tbl = phot_plugin.export_table()
        assert len(tbl) == 1

        phot_plugin.dataset.selected = 'no_wcs[SCI,1]'
        phot_plugin._obj.vue_do_aper_phot()
        tbl = phot_plugin.export_table()
        assert len(tbl) == 1  # Old table discarded due to incompatible column
        assert_array_equal(tbl['sky_center'], None)


class TestAdvancedAperPhot:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_helper):
        # Reference image
        fn_1 = get_pkg_data_filename('data/gauss100_fits_wcs.fits')
        imviz_helper.load_data(fn_1)
        # Different pixel scale
        imviz_helper.load_data(get_pkg_data_filename('data/gauss100_fits_wcs_block_reduced.fits'))
        # Different pixel scale + rotated
        imviz_helper.load_data(get_pkg_data_filename('data/gauss100_fits_wcs_block_reduced_rotated.fits'))  # noqa: E501

        # Link them by WCS
        imviz_helper.link_data(align_by='wcs')
        w = imviz_helper.app.data_collection[0].coords

        # Regions to be used for aperture photometry
        imviz_helper.plugins['Subset Tools'].import_region([
            CirclePixelRegion(center=PixCoord(x=145.1, y=168.3), radius=5).to_sky(w),
            CirclePixelRegion(center=PixCoord(x=48.3, y=200.3), radius=5).to_sky(w),
            EllipsePixelRegion(center=PixCoord(x=84.7, y=224.1), width=23, height=9, angle=2.356 * u.rad).to_sky(w),  # noqa: E501
            RectanglePixelRegion(center=PixCoord(x=229, y=152), width=17, height=7).to_sky(w)],
            combination_mode='new')

        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer._obj
        self.phot_plugin = imviz_helper.plugins["Aperture Photometry"]

    @pytest.mark.parametrize(('data_label', 'local_bkg'), [
        ('gauss100_fits_wcs[PRIMARY,1]', 5.0),
        ('gauss100_fits_wcs_block_reduced[PRIMARY,1]', 20.0),
        ('gauss100_fits_wcs_block_reduced_rotated[PRIMARY,1]', 20.0)])
    @pytest.mark.parametrize(('subset_label', 'expected_sum'), [
        ('Subset 1', 738.8803424408962),
        ('Subset 2', 857.5194857987592),
        ('Subset 3', 472.17364321556005),
        ('Subset 4', 837.0023608207703)])
    def test_aperphot(self, data_label, local_bkg, subset_label, expected_sum):
        """All data should give similar result for the same Subset."""
        self.phot_plugin.dataset.selected = data_label
        self.phot_plugin.aperture.selected = subset_label
        self.phot_plugin.background.selected = 'Manual'
        self.phot_plugin.background_value = local_bkg
        self.phot_plugin._obj.vue_do_aper_phot()
        tbl = self.phot_plugin.export_table()

        # Imperfect down-sampling and imperfect apertures, so 10% is good enough.
        assert_allclose(tbl['sum'][-1], expected_sum, rtol=0.1)

    @pytest.mark.parametrize(('data_label', 'fac'), [
        ('gauss100_fits_wcs[PRIMARY,1]', 1),
        ('gauss100_fits_wcs_block_reduced[PRIMARY,1]', 4),
        ('gauss100_fits_wcs_block_reduced_rotated[PRIMARY,1]', 4)
    ])
    @pytest.mark.parametrize(('bg_label', 'expected_bg'), [
        ('Subset 2', 12.269274711608887),
        ('Subset 3', 7.935906410217285),
        ('Subset 4', 11.120951652526855)])
    def test_sky_background(self, data_label, fac, bg_label, expected_bg):
        """All background (median) should give similar result for the same Subset.
        Down-sampled data has higher factor due to flux conservation.
        """
        self.phot_plugin.dataset.selected = data_label
        self.phot_plugin.aperture.selected = "Subset 1"  # Does not matter
        self.phot_plugin.background.selected = bg_label

        # Imperfect down-sampling and abusing apertures, so 10% is good enough.
        assert_allclose(float(self.phot_plugin.background_value), expected_bg * fac, rtol=0.1)


def test_annulus_background(imviz_helper):
    gauss4 = make_4gaussians_image()  # The background has a mean of 5 with noise
    ones = np.ones(gauss4.shape)
    bg_4gauss_1 = 5.802287
    bg_4gauss_2 = 5.052332
    bg_4gauss_3 = 45.416834
    bg_4gauss_4 = 4.939397

    imviz_helper.load_data(gauss4, data_label='four_gaussians')
    imviz_helper.load_data(ones, data_label='ones')

    phot_plugin = imviz_helper.plugins['Aperture Photometry']
    phot_plugin.dataset.selected = 'ones'

    # Mark an object of interest
    circle_1 = CirclePixelRegion(center=PixCoord(x=150, y=25), radius=7)
    # Load annulus (this used to be part of the plugin but no longer)
    annulus_1 = CircleAnnulusPixelRegion(
        PixCoord(x=150, y=25), inner_radius=7, outer_radius=17)
    imviz_helper.plugins['Subset Tools'].import_region([circle_1, annulus_1],
                                                       combination_mode='new')

    phot_plugin.aperture.selected = 'Subset 1'
    phot_plugin.background.selected = 'Subset 2'

    # Check annulus for ones
    assert_allclose(phot_plugin.background_value, 1)

    # Switch data
    phot_plugin.dataset.selected = 'four_gaussians'
    assert_allclose(phot_plugin.background_value, bg_4gauss_1)  # Changed

    # Draw ellipse on another object
    ellipse_1 = EllipsePixelRegion(center=PixCoord(x=20.5, y=37.5), width=41, height=15)
    # Load annulus (this used to be part of the plugin but no longer)
    annulus_2 = CircleAnnulusPixelRegion(
        PixCoord(x=20.5, y=37.5), inner_radius=20.5, outer_radius=30.5)
    imviz_helper.plugins['Subset Tools'].import_region([ellipse_1, annulus_2],
                                                       combination_mode='new')

    # Subset 4 (annulus) should be available in both sets of choices, but invalid for selection as
    # aperture
    assert 'Subset 4' in phot_plugin.aperture.choices
    assert 'Subset 4' in phot_plugin.background.choices

    phot_plugin.aperture.selected = 'Subset 4'
    assert not phot_plugin.aperture.selected_validity.get('is_aperture', True)
    with pytest.raises(ValueError, match="Selected aperture is not valid"):
        phot_plugin.calculate_photometry()

    phot_plugin.aperture.selected = 'Subset 3'
    assert phot_plugin.aperture.selected_validity.get('is_aperture', False)
    phot_plugin.background.selected = 'Subset 4'

    # Check new annulus for four_gaussians
    assert_allclose(phot_plugin.background_value, bg_4gauss_2)  # Changed

    # Switch to manual, should not change
    phot_plugin.background.selected = 'Manual'
    assert_allclose(phot_plugin.background_value, bg_4gauss_2)

    # Switch to Subset, should change a lot because this is not background area
    phot_plugin.background.selected = 'Subset 1'
    assert_allclose(phot_plugin.background_value, bg_4gauss_3)

    # Switch back to annulus, should be same as before in same mode
    phot_plugin.background.selected = 'Subset 4'
    assert_allclose(phot_plugin.background_value, bg_4gauss_2)

    # Edit the annulus and make sure background updates
    subset_plugin = imviz_helper.plugins['Subset Tools']._obj
    subset_plugin.subset_selected = "Subset 4"
    subset_plugin._set_value_in_subset_definition(0, "X Center (pixels)", "value", 25.5)
    subset_plugin._set_value_in_subset_definition(0, "Y Center (pixels)", "value", 42.5)
    subset_plugin._set_value_in_subset_definition(0, "Inner Radius (pixels)", "value", 40)
    subset_plugin._set_value_in_subset_definition(0, "Outer Radius (pixels)", "value", 45)
    subset_plugin.vue_update_subset()
    assert_allclose(phot_plugin.background_value, bg_4gauss_4)


def test_fit_radial_profile_with_nan(imviz_helper):
    gauss4 = make_4gaussians_image()  # The background has a mean of 5 with noise
    # Insert NaN
    gauss4[25, 150] = np.nan

    imviz_helper.load_data(gauss4, data_label='four_gaussians')

    # Mark an object of interest
    circle_1 = CirclePixelRegion(center=PixCoord(x=150, y=25), radius=7)
    imviz_helper.plugins['Subset Tools'].import_region(
        [circle_1], combination_mode='new')

    phot_plugin = imviz_helper.plugins['Aperture Photometry']
    phot_plugin.dataset.selected = 'four_gaussians'
    phot_plugin.aperture.selected = 'Subset 1'
    phot_plugin.current_plot_type = 'Radial Profile'
    phot_plugin.fit_radial_profile = True
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Fitter warnings do not matter, only want error.
        phot_plugin._obj.vue_do_aper_phot()
    tbl = imviz_helper.plugins['Aperture Photometry'].export_table()

    assert phot_plugin._obj.result_failed_msg == ''
    assert_allclose(tbl['sum'][0], 8590.419296)


# NOTE: Extracting the cutout for radial profile is aperture
#       shape agnostic, so we use ellipse as representative case.
# NOTE: This test only tests the radial profile algorithm and does
#       not care if the actual plugin use centroid or not.
class TestRadialProfile():
    def setup_class(self):
        data = np.ones((51, 51)) * u.nJy
        aperture = EllipticalAperture((25, 25), 20, 15)
        phot_aperstats = ApertureStats(data, aperture)
        self.data = data
        self.bbox = phot_aperstats.bbox
        self.centroid = phot_aperstats.centroid

    def test_profile_raw(self):
        x_arr, y_arr = _radial_profile(self.data, self.bbox, self.centroid, raw=True)
        # Too many data points to compare each one for X.
        assert x_arr.shape == y_arr.shape == (1371, )
        assert_allclose(x_arr.min(), 0)
        assert_allclose(x_arr.max(), 21)
        assert_allclose(y_arr, 1)

    def test_profile_imexam(self):
        x_arr, y_arr = _radial_profile(self.data, self.bbox, self.centroid, raw=False)
        assert_allclose(x_arr, np.arange(21) + 0.5)
        assert_allclose(y_arr, 1)


# NOTE: This test only tests the curve of growth algorithm and does
#       not care if the actual plugin use centroid or not.
@pytest.mark.parametrize('with_unit', (False, True))
def test_curve_of_growth(with_unit):
    data = np.ones((51, 51))
    cen = (25, 25)
    if with_unit:
        data = data << (u.MJy / u.sr)
        data_unit = data.unit.to_string()
        bg = 0 * data.unit
        pixarea_fac = 1 * u.sr
        expected_ylabel = 'MJy'
    else:
        data_unit = None
        bg = 0
        pixarea_fac = None
        expected_ylabel = 'Value'

    apertures = (CircularAperture(cen, 20),
                 EllipticalAperture(cen, 20, 15),
                 RectangularAperture(cen, 40, 30))

    for aperture in apertures:
        astat = ApertureStats(data, aperture)
        x_arr, sum_arr, x_label, y_label = _curve_of_growth(
            data, astat.centroid, aperture, background=bg, pixarea_fac=pixarea_fac,
            image_unit=data_unit)
        assert_allclose(x_arr, [2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
        assert y_label == expected_ylabel
        assert x_label == 'Radius (pix)'
        assert_allclose(sum_arr, [
            12.566371, 50.265482, 113.097336, 201.06193, 314.159265,
            452.389342, 615.75216, 804.247719, 1017.87602, 1256.637061])

    with pytest.raises(TypeError, match='Unsupported aperture'):
        _curve_of_growth(data, cen, EllipticalAnnulus(cen, 3, 8, 5), pixarea_fac=pixarea_fac)


def test_cubeviz_batch(cubeviz_helper, spectrum1d_cube_fluxunit_jy_per_steradian):
    cubeviz_helper.load_data(spectrum1d_cube_fluxunit_jy_per_steradian, data_label='test')
    phot_plugin = cubeviz_helper.plugins['Aperture Photometry']
    uc_plugin = cubeviz_helper.plugins['Unit Conversion']
    subset_plugin = cubeviz_helper.plugins['Subset Tools']

    subset_plugin.import_region(CirclePixelRegion(center=PixCoord(x=5, y=5), radius=2),
                                combination_mode='new')
    subset_plugin.import_region(CirclePixelRegion(center=PixCoord(x=3, y=3), radius=2),
                                combination_mode='new')

    phot_plugin.dataset.selected = 'test[FLUX]'
    phot_plugin.multiselect = True
    phot_plugin.aperture.selected = ['Subset 1', 'Subset 2']

    phot_plugin.calculate_batch_photometry(full_exceptions=True)
    assert len(phot_plugin.table._obj) == 2
    tbl = cubeviz_helper.plugins['Aperture Photometry'].export_table()
    assert_quantity_allclose(tbl['sum'], [5.980836e-12, 2.037396e-10] * u.Jy, rtol=1e-4)

    # Test that it still works after unit conversion
    uc_plugin.flux_unit = 'MJy'

    phot_plugin.calculate_batch_photometry(full_exceptions=True)

    assert len(phot_plugin.table._obj) == 4
    tbl = cubeviz_helper.plugins['Aperture Photometry'].export_table()
    # get_aperture_photometry_results converts all to the same units
    assert_quantity_allclose(tbl['sum'],
                             [5.980836e-12, 2.037396e-10, 5.980836e-12, 2.037396e-10] * u.Jy,
                             rtol=1e-4)
