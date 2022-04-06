import pytest
import numpy as np
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from numpy.testing import assert_allclose, assert_array_equal

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS, BaseImviz_WCS_NoWCS


class TestSimpleAperPhot(BaseImviz_WCS_WCS):
    def test_plugin_wcs_dithered(self):
        self.imviz.link_data(link_type='wcs')  # They are dithered by 1 pixel on X
        self.imviz._apply_interactive_region('bqplot:circle', (0, 0), (9, 9))  # Draw a circle

        phot_plugin = self.imviz.app.get_tray_item_from_name('imviz-aper-phot-simple')

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
        assert phot_plugin.bg_subset.labels == ['Manual', 'Annulus', 'Subset 1']
        assert_allclose(phot_plugin.background_value, 0)
        assert_allclose(phot_plugin.counts_factor, 0)
        assert_allclose(phot_plugin.pixel_area, 0)
        assert_allclose(phot_plugin.flux_scaling, 0)
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 2
        assert phot_plugin.plot_available
        assert phot_plugin.radial_plot != ''  # Does not check content

        # Check photometry results.
        assert tbl.colnames == [
            'id', 'xcentroid', 'ycentroid', 'sky_centroid', 'background', 'sum',
            'sum_aper_area', 'pixarea_tot', 'aperture_sum_counts', 'aperture_sum_counts_err',
            'counts_fac', 'aperture_sum_mag', 'flux_scaling', 'min', 'max', 'mean', 'median',
            'mode', 'std', 'mad_std', 'var', 'biweight_location', 'biweight_midvariance',
            'fwhm', 'semimajor_sigma', 'semiminor_sigma', 'orientation', 'eccentricity',
            'data_label', 'subset_label', 'timestamp']
        assert_array_equal(tbl['id'], [1, 2])
        assert_allclose(tbl['background'], 0)
        assert_quantity_allclose(tbl['sum_aper_area'], 63.617251 * (u.pix * u.pix))
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

        # BUG: https://github.com/glue-viz/glue-astronomy/issues/52
        # Sky should have been the same and the pix different, but not until bug is fixed.
        # The aperture sum might be different too if mask is off limit in second image.
        assert_quantity_allclose(tbl['xcentroid'], 4.5 * u.pix)
        assert_quantity_allclose(tbl['ycentroid'], 4.5 * u.pix)
        sky = tbl['sky_centroid']
        assert_allclose(sky.ra.deg, [337.518943, 337.519241])
        assert_allclose(sky.dec.deg, [-20.832083, -20.832083])
        assert_allclose(tbl['sum'], 63.61725123519332)

        # Make sure it also works on an ellipse subset.
        self.imviz._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 4))
        phot_plugin.dataset_selected = 'has_wcs_1[SCI,1]'
        phot_plugin.subset_selected = 'Subset 2'
        phot_plugin.current_plot_type = 'Radial Profile'
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 3  # New result is appended
        assert tbl[-1]['id'] == 3
        assert_quantity_allclose(tbl[-1]['xcentroid'], 4.5 * u.pix)
        assert_quantity_allclose(tbl[-1]['ycentroid'], 2 * u.pix)
        sky = tbl[-1]['sky_centroid']
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
        assert np.isnan(tbl[-1]['xcentroid'])
        assert np.isnan(tbl[-1]['ycentroid'])
        sky = tbl[-1]['sky_centroid']
        assert np.isnan(sky.ra.deg)
        assert np.isnan(sky.dec.deg)
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
        assert_array_equal(tbl['sky_centroid'], None)


def test_annulus_background(imviz_helper):
    from photutils.datasets import make_4gaussians_image

    gauss4 = make_4gaussians_image()  # The background has a mean of 5 with noise
    ones = np.ones(gauss4.shape)

    imviz_helper.load_data(gauss4, data_label='four_gaussians')
    imviz_helper.load_data(ones, data_label='ones')

    phot_plugin = imviz_helper.app.get_tray_item_from_name('imviz-aper-phot-simple')
    phot_plugin.dataset_selected = 'ones'

    # Mark an object of interest
    imviz_helper._apply_interactive_region('bqplot:circle', (143, 18), (157, 32))
    phot_plugin.subset_selected = 'Subset 1'
    phot_plugin.bg_subset_selected = 'Annulus'

    # Check annulus for ones
    assert_allclose(phot_plugin.bg_annulus_inner_r, 7)  # From circle
    assert_allclose(phot_plugin.bg_annulus_width, 10)  # Default
    assert_allclose(phot_plugin.background_value, 1)

    # Switch data
    phot_plugin.dataset_selected = 'four_gaussians'
    assert_allclose(phot_plugin.bg_annulus_inner_r, 7)  # Unchanged
    assert_allclose(phot_plugin.bg_annulus_width, 10)
    assert_allclose(phot_plugin.background_value, 5.745596129482831)  # Changed

    # Draw ellipse on another object
    imviz_helper._apply_interactive_region('bqplot:ellipse', (0, 30), (41, 45))
    phot_plugin.subset_selected = 'Subset 2'

    # Check new annulus for four_gaussians
    assert_allclose(phot_plugin.bg_annulus_inner_r, 20.5)  # From ellipse half-width
    assert_allclose(phot_plugin.bg_annulus_width, 10)  # Unchanged
    assert_allclose(phot_plugin.background_value, 5.13918435824334)  # Changed

    # Switch to manual, should not change
    phot_plugin.bg_subset_selected = 'Manual'
    assert_allclose(phot_plugin.background_value, 5.13918435824334)

    # Switch to Subset, should change a lot because this is not background area
    phot_plugin.bg_subset_selected = 'Subset 1'
    assert_allclose(phot_plugin.background_value, 44.72559981461203)

    # Switch back to annulus, should be same as before in same mode
    phot_plugin.bg_subset_selected = 'Annulus'
    assert_allclose(phot_plugin.bg_annulus_inner_r, 20.5)
    assert_allclose(phot_plugin.bg_annulus_width, 10)
    assert_allclose(phot_plugin.background_value, 5.13918435824334)

    # Manually change inner_r
    phot_plugin.bg_annulus_inner_r = 40
    assert_allclose(phot_plugin.background_value, 4.783765940615679)

    # Manually change width
    phot_plugin.bg_annulus_width = 5
    assert_allclose(phot_plugin.background_value, 4.894003242594493)

    # Bad annulus should not crash plugin
    phot_plugin.bg_annulus_inner_r = -1
    assert_allclose(phot_plugin.background_value, 0)
