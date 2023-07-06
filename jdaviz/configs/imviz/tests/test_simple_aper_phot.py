import pytest
import numpy as np
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from numpy.testing import assert_allclose, assert_array_equal
from photutils.aperture import (ApertureStats, CircularAperture, EllipticalAperture,
                                RectangularAperture, EllipticalAnnulus)
from regions import CircleAnnulusPixelRegion, PixCoord

from jdaviz.configs.imviz.plugins.aper_phot_simple.aper_phot_simple import (
    _curve_of_growth, _radial_profile)
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS, BaseImviz_WCS_NoWCS


class TestSimpleAperPhot(BaseImviz_WCS_WCS):
    def test_plugin_wcs_dithered(self):
        self.imviz.link_data(link_type='wcs')  # They are dithered by 1 pixel on X
        self.imviz._apply_interactive_region('bqplot:circle', (0, 0), (9, 9))  # Draw a circle

        phot_plugin = self.imviz.app.get_tray_item_from_name('imviz-aper-phot-simple')

        # Model fitting is already tested in astropy.
        # Here, we enable it just to make sure it does not crash.
        phot_plugin.fit_radial_profile = True

        # Make sure invalid Data/Subset selection does not crash plugin.
        with pytest.raises(ValueError):
            phot_plugin.dataset_selected = 'no_such_data'
        with pytest.raises(ValueError):
            # will raise an error and revert to first entry
            phot_plugin.subset_selected = 'no_such_subset'
        assert phot_plugin.subset_selected == ''
        phot_plugin.subset_selected = phot_plugin.subset.labels[0]
        assert_allclose(phot_plugin.background_value, 0)

        phot_plugin.dataset_selected = 'has_wcs_1[SCI,1]'
        phot_plugin.subset_selected = phot_plugin.subset.labels[0]
        with pytest.raises(ValueError):
            phot_plugin.bg_subset_selected = 'no_such_subset'
        assert phot_plugin.bg_subset_selected == 'Manual'
        assert_allclose(phot_plugin.background_value, 0)

        # Perform photometry on both images using same Subset.
        phot_plugin.dataset_selected = 'has_wcs_1[SCI,1]'
        phot_plugin.subset_selected = 'Subset 1'
        assert phot_plugin._selected_data is not None
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 1

        phot_plugin.dataset_selected = 'has_wcs_2[SCI,1]'
        phot_plugin.current_plot_type = 'Radial Profile (Raw)'
        assert phot_plugin._selected_data is not None
        assert phot_plugin._selected_subset is not None
        assert phot_plugin.bg_subset.labels == ['Manual', 'Subset 1']
        assert_allclose(phot_plugin.background_value, 0)
        assert_allclose(phot_plugin.counts_factor, 0)
        assert_allclose(phot_plugin.pixel_area, 0)
        assert_allclose(phot_plugin.flux_scaling, 0)
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 2
        assert phot_plugin.plot_available
        assert len(phot_plugin.plot.marks['scatter'].x) > 0

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
        assert_quantity_allclose(tbl['sum_aper_area'], [63.617251, 62.22684693104279] * (u.pix * u.pix))  # noqa
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
        assert_quantity_allclose(tbl['xcenter'], [4.5, 5.5] * u.pix)
        assert_quantity_allclose(tbl['ycenter'], 4.5 * u.pix)
        sky = tbl['sky_center']
        assert_allclose(sky.ra.deg, 337.518943)
        assert_allclose(sky.dec.deg, -20.832083)
        assert_allclose(tbl['sum'], [63.617251, 62.22684693104279])

        # Make sure it also works on an ellipse subset.
        self.imviz._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 4))
        phot_plugin.dataset_selected = 'has_wcs_1[SCI,1]'
        phot_plugin.subset_selected = 'Subset 2'
        phot_plugin.current_plot_type = 'Radial Profile'
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 3  # New result is appended
        assert tbl[-1]['id'] == 3
        assert_quantity_allclose(tbl[-1]['xcenter'], 4.5 * u.pix)
        assert_quantity_allclose(tbl[-1]['ycenter'], 2 * u.pix)
        sky = tbl[-1]['sky_center']
        assert_allclose(sky.ra.deg, 337.51894336144454)
        assert_allclose(sky.dec.deg, -20.832777499255897)
        assert_quantity_allclose(tbl[-1]['sum_aper_area'], 28.274334 * (u.pix * u.pix))
        assert_allclose(tbl[-1]['sum'], 28.274334)
        assert_allclose(tbl[-1]['mean'], 1)
        assert tbl[-1]['data_label'] == 'has_wcs_1[SCI,1]'
        assert tbl[-1]['subset_label'] == 'Subset 2'

        # Make sure it also works on a rectangle subset.
        # We also subtract off background from itself here.
        self.imviz._apply_interactive_region('bqplot:rectangle', (0, 0), (9, 9))
        phot_plugin.dataset_selected = 'has_wcs_1[SCI,1]'
        phot_plugin.subset_selected = 'Subset 3'
        phot_plugin.bg_subset_selected = 'Subset 3'
        assert_allclose(phot_plugin.background_value, 1)
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 4  # New result is appended
        assert tbl[-1]['id'] == 4
        assert_quantity_allclose(tbl[-1]['xcenter'], 4.5 * u.pix)
        assert_quantity_allclose(tbl[-1]['ycenter'], 4.5 * u.pix)
        sky = tbl[-1]['sky_center']
        assert_allclose(sky.ra.deg, 337.51894336144454)
        assert_allclose(sky.dec.deg, -20.832083)
        assert_quantity_allclose(tbl[-1]['sum_aper_area'], 81 * (u.pix * u.pix))
        assert_allclose(tbl[-1]['sum'], 0)
        assert_allclose(tbl[-1]['mean'], 0)
        assert tbl[-1]['data_label'] == 'has_wcs_1[SCI,1]'
        assert tbl[-1]['subset_label'] == 'Subset 3'

        # Make sure background auto-updates.
        phot_plugin.bg_subset_selected = 'Manual'
        assert_allclose(phot_plugin.background_value, 1)  # Keeps last value
        phot_plugin.bg_subset_selected = 'Subset 1'
        assert_allclose(phot_plugin.background_value, 1)
        self.imviz.load_data(np.ones((10, 10)) + 1, data_label='twos')
        phot_plugin.dataset_selected = 'twos'
        assert_allclose(phot_plugin.background_value, 2)  # Recalculate based on new Data

        # Curve of growth
        phot_plugin.current_plot_type = 'Curve of Growth'
        phot_plugin.vue_do_aper_phot()
        assert phot_plugin.plot.figure.title == 'Curve of growth from aperture center'


class TestSimpleAperPhot_NoWCS(BaseImviz_WCS_NoWCS):
    def test_plugin_no_wcs(self):
        # Most things already tested above, so not re-tested here.
        self.imviz._apply_interactive_region('bqplot:circle', (0, 0), (9, 9))  # Draw a circle
        phot_plugin = self.imviz.app.get_tray_item_from_name('imviz-aper-phot-simple')

        phot_plugin.dataset_selected = 'has_wcs[SCI,1]'
        phot_plugin.subset_selected = 'Subset 1'
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 1

        phot_plugin.dataset_selected = 'no_wcs[SCI,1]'
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 1  # Old table discarded due to incompatible column
        assert_array_equal(tbl['sky_center'], None)


def test_annulus_background(imviz_helper):
    from photutils.datasets import make_4gaussians_image

    gauss4 = make_4gaussians_image()  # The background has a mean of 5 with noise
    ones = np.ones(gauss4.shape)

    imviz_helper.load_data(gauss4, data_label='four_gaussians')
    imviz_helper.load_data(ones, data_label='ones')

    phot_plugin = imviz_helper.app.get_tray_item_from_name('imviz-aper-phot-simple')
    phot_plugin.dataset_selected = 'ones'

    # Mark an object of interest
    # CirclePixelRegion(center=PixCoord(x=150, y=25), radius=7)
    imviz_helper._apply_interactive_region('bqplot:circle', (143, 18), (157, 32))

    # Load annulus (this used to be part of the plugin but no longer)
    annulus_1 = CircleAnnulusPixelRegion(
        PixCoord(x=150, y=25), inner_radius=7, outer_radius=17)
    imviz_helper.load_regions([annulus_1])

    phot_plugin.subset_selected = 'Subset 1'
    phot_plugin.bg_subset_selected = 'Subset 2'

    # Check annulus for ones
    assert_allclose(phot_plugin.background_value, 1)

    # Switch data
    phot_plugin.dataset_selected = 'four_gaussians'
    assert_allclose(phot_plugin.background_value, 5.745596129482831)  # Changed

    # Draw ellipse on another object
    # EllipsePixelRegion(center=PixCoord(x=20.5, y=37.5), width=41, height=15)
    imviz_helper._apply_interactive_region('bqplot:ellipse', (0, 30), (41, 45))

    # Load annulus (this used to be part of the plugin but no longer)
    annulus_2 = CircleAnnulusPixelRegion(
        PixCoord(x=20.5, y=37.5), inner_radius=20.5, outer_radius=30.5)
    imviz_helper.load_regions([annulus_2])

    # Subset 4 (annulus) should be available for the background but not the aperture
    assert 'Subset 4' not in phot_plugin.subset.choices
    assert 'Subset 4' in phot_plugin.bg_subset.choices

    phot_plugin.subset_selected = 'Subset 3'
    phot_plugin.bg_subset_selected = 'Subset 4'

    # Check new annulus for four_gaussians
    assert_allclose(phot_plugin.background_value, 5.13918435824334)  # Changed

    # Switch to manual, should not change
    phot_plugin.bg_subset_selected = 'Manual'
    assert_allclose(phot_plugin.background_value, 5.13918435824334)

    # Switch to Subset, should change a lot because this is not background area
    phot_plugin.bg_subset_selected = 'Subset 1'
    assert_allclose(phot_plugin.background_value, 44.72559981461203)

    # Switch back to annulus, should be same as before in same mode
    phot_plugin.bg_subset_selected = 'Subset 4'
    assert_allclose(phot_plugin.background_value, 5.13918435824334)

    # Edit the annulus and make sure background updates
    subset_plugin = imviz_helper.plugins["Subset Tools"]._obj
    subset_plugin.subset_selected = "Subset 4"
    subset_plugin._set_value_in_subset_definition(0, "X Center", "value", 25.5)
    subset_plugin._set_value_in_subset_definition(0, "Y Center", "value", 42.5)
    subset_plugin._set_value_in_subset_definition(0, "Inner radius", "value", 40)
    subset_plugin._set_value_in_subset_definition(0, "Outer radius", "value", 45)
    subset_plugin.vue_update_subset()
    assert_allclose(phot_plugin.background_value, 4.89189)


# NOTE: Extracting the cutout for radial profile is aperture
#       shape agnostic, so we use ellipse as representative case.
# NOTE: This test only tests the radial profile algorithm and does
#       not care if the actual plugin use centroid or not.
class TestRadialProfile():
    def setup_class(self):
        data = np.ones((51, 51)) * u.nJy
        aperture = EllipticalAperture((25, 25), 20, 15)
        phot_aperstats = ApertureStats(data, aperture)
        self.data_cutout = phot_aperstats.data_cutout
        self.bbox = phot_aperstats.bbox
        self.centroid = phot_aperstats.centroid

    def test_profile_raw(self):
        x_arr, y_arr = _radial_profile(self.data_cutout, self.bbox, self.centroid, raw=True)
        # Too many data points to compare each one for X.
        assert x_arr.shape == y_arr.shape == (923, )
        assert_allclose(x_arr.min(), 0)
        assert_allclose(x_arr.max(), 19.4164878389476)
        assert_allclose(y_arr, 1)

    def test_profile_imexam(self):
        x_arr, y_arr = _radial_profile(self.data_cutout, self.bbox, self.centroid, raw=False)
        assert_allclose(x_arr, range(20))
        assert_allclose(y_arr, 1)


# NOTE: This test only tests the curve of growth algorithm and does
#       not care if the actual plugin use centroid or not.
@pytest.mark.parametrize('with_unit', (False, True))
def test_curve_of_growth(with_unit):
    data = np.ones((51, 51))
    cen = (25, 25)
    if with_unit:
        data = data << (u.MJy / u.sr)
        bg = 0 * data.unit
        pixarea_fac = 1 * u.sr
        expected_ylabel = 'MJy'
    else:
        bg = 0
        pixarea_fac = None
        expected_ylabel = 'Value'

    apertures = (CircularAperture(cen, 20),
                 EllipticalAperture(cen, 20, 15),
                 RectangularAperture(cen, 20, 15))

    for aperture in apertures:
        astat = ApertureStats(data, aperture)
        final_sum = astat.sum
        if pixarea_fac is not None:
            final_sum = final_sum * pixarea_fac
        x_arr, sum_arr, x_label, y_label = _curve_of_growth(
            data, astat.centroid, aperture, final_sum, background=bg, pixarea_fac=pixarea_fac)
        assert_allclose(x_arr, [2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
        assert y_label == expected_ylabel

        if isinstance(aperture, CircularAperture):
            assert x_label == 'Radius (pix)'
            assert_allclose(sum_arr, [
                12.566371, 50.265482, 113.097336, 201.06193, 314.159265,
                452.389342, 615.75216, 804.247719, 1017.87602, 1256.637061])
        elif isinstance(aperture, EllipticalAperture):
            assert x_label == 'Semimajor axis (pix)'
            assert_allclose(sum_arr, [
                9.424778, 37.699112, 84.823002, 150.796447, 235.619449,
                339.292007, 461.81412, 603.185789, 763.407015, 942.477796])
        else:  # RectangularAperture
            assert x_label == 'Width (pix)'
            assert_allclose(sum_arr, [3, 12, 27, 48, 75, 108, 147, 192, 243, 300])

    with pytest.raises(TypeError, match='Unsupported aperture'):
        _curve_of_growth(data, cen, EllipticalAnnulus(cen, 3, 8, 5), 100,
                         pixarea_fac=pixarea_fac)
