import numpy as np
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from numpy.testing import assert_allclose, assert_array_equal

from jdaviz.configs.imviz.plugins.aper_phot_simple.aper_phot_simple import SimpleAperturePhotometry
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS, BaseImviz_WCS_NoWCS


class TestSimpleAperPhot(BaseImviz_WCS_WCS):
    def test_plugin_wcs_dithered(self):
        self.imviz.link_data(link_type='wcs')  # They are dithered by 1 pixel on X
        self.imviz._apply_interactive_region('bqplot:circle', (0, 0), (9, 9))  # Draw a circle

        phot_plugin = SimpleAperturePhotometry(app=self.imviz.app)

        # Populate plugin menu items.
        phot_plugin._on_viewer_data_changed()

        # Make sure invalid Data/Subset selection does not crash plugin.
        phot_plugin.data_selected = 'no_such_data'
        assert phot_plugin._selected_data is None
        phot_plugin.subset_selected = 'no_such_subset'
        assert phot_plugin._selected_subset is None
        phot_plugin.bg_subset_selected = 'no_such_subset'
        assert_allclose(phot_plugin.background_value, 0)
        phot_plugin.vue_do_aper_phot()
        assert not phot_plugin.result_available
        assert len(phot_plugin.results) == 0
        assert self.imviz.get_aperture_photometry_results() is None
        assert not phot_plugin.plot_available
        assert phot_plugin.radial_plot == ''
        assert phot_plugin.current_plot_type == 'Radial Profile'  # Software default

        phot_plugin.data_selected = 'has_wcs_1[SCI,1]'
        phot_plugin.subset_selected = 'no_such_subset'
        assert phot_plugin._selected_subset is None
        phot_plugin.bg_subset_selected = 'no_such_subset'
        assert_allclose(phot_plugin.background_value, 0)

        # Perform photometry on both images using same Subset.
        phot_plugin.subset_selected = 'Subset 1'
        phot_plugin.vue_do_aper_phot()
        phot_plugin.data_selected = 'has_wcs_2[SCI,1]'
        phot_plugin.current_plot_type = 'Radial Profile (Raw)'
        phot_plugin.vue_do_aper_phot()
        assert phot_plugin.bg_subset_items == ['Manual', 'Subset 1']
        assert_allclose(phot_plugin.background_value, 0)
        assert_allclose(phot_plugin.counts_factor, 0)
        assert_allclose(phot_plugin.pixel_area, 0)
        assert_allclose(phot_plugin.flux_scaling, 0)
        assert phot_plugin.plot_available
        assert phot_plugin.radial_plot != ''  # Does not check content

        # Check photometry results.
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 2
        assert tbl.colnames == [
            'id', 'xcenter', 'ycenter', 'sky_center', 'background', 'npix', 'aperture_sum',
            'pixarea_tot', 'aperture_sum_counts', 'aperture_sum_counts_err', 'counts_fac',
            'aperture_sum_mag', 'flux_scaling', 'mean', 'stddev', 'median', 'min', 'max',
            'data_label', 'subset_label', 'timestamp']
        assert_array_equal(tbl['id'], [1, 2])
        assert_allclose(tbl['background'], 0)
        assert_quantity_allclose(tbl['npix'], 63.617251235193315 * u.pix)
        assert_array_equal(tbl['pixarea_tot'], None)
        assert_array_equal(tbl['aperture_sum_counts'], None)
        assert_array_equal(tbl['aperture_sum_counts_err'], None)
        assert_array_equal(tbl['counts_fac'], None)
        assert_array_equal(tbl['aperture_sum_mag'], None)
        assert_array_equal(tbl['flux_scaling'], None)
        assert_allclose(tbl['mean'], 1)
        assert_allclose(tbl['stddev'], 0)
        assert_allclose(tbl['median'], 1)
        assert_allclose(tbl['min'], 1)
        assert_allclose(tbl['max'], 1)
        assert_array_equal(tbl['data_label'], ['has_wcs_1[SCI,1]', 'has_wcs_2[SCI,1]'])
        assert_array_equal(tbl['subset_label'], ['Subset 1', 'Subset 1'])
        assert tbl['timestamp'].scale == 'utc'

        # BUG: https://github.com/glue-viz/glue-astronomy/issues/52
        # Sky should have been the same and the pix different, but not until bug is fixed.
        # The aperture sum might be different too if mask is off limit in second image.
        assert_quantity_allclose(tbl['xcenter'], 4.5 * u.pix)
        assert_quantity_allclose(tbl['ycenter'], 4.5 * u.pix)
        sky = tbl['sky_center']
        assert_allclose(sky.ra.deg, [337.518943, 337.519241])
        assert_allclose(sky.dec.deg, [-20.832083, -20.832083])
        assert_allclose(tbl['aperture_sum'], 63.61725123519332)

        # Make sure it also works on an ellipse subset.
        self.imviz._apply_interactive_region('bqplot:ellipse', (0, 0), (9, 4))
        phot_plugin._on_viewer_data_changed()
        phot_plugin.data_selected = 'has_wcs_1[SCI,1]'
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
        assert_quantity_allclose(tbl[-1]['npix'], 7.068583470577035 * u.pix)
        assert_allclose(tbl[-1]['aperture_sum'], 7.068583470577034)
        assert_allclose(tbl[-1]['mean'], 1)
        assert tbl[-1]['data_label'] == 'has_wcs_1[SCI,1]'
        assert tbl[-1]['subset_label'] == 'Subset 2'

        # Make sure it also works on a rectangle subset.
        # We also subtract off background from itself here.
        self.imviz._apply_interactive_region('bqplot:rectangle', (0, 0), (9, 9))
        phot_plugin._on_viewer_data_changed()
        phot_plugin.data_selected = 'has_wcs_1[SCI,1]'
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
        assert_allclose(sky.ra.deg, 337.518943)
        assert_allclose(sky.dec.deg, -20.832083)
        assert_quantity_allclose(tbl[-1]['npix'], 81 * u.pix)
        assert_allclose(tbl[-1]['aperture_sum'], 0)
        assert_allclose(tbl[-1]['mean'], 0)
        assert tbl[-1]['data_label'] == 'has_wcs_1[SCI,1]'
        assert tbl[-1]['subset_label'] == 'Subset 3'

        # Make sure background auto-updates.
        phot_plugin.bg_subset_selected = 'Manual'
        assert_allclose(phot_plugin.background_value, 1)  # Keeps last value
        phot_plugin.bg_subset_selected = 'Subset 1'
        assert_allclose(phot_plugin.background_value, 1)
        self.imviz.load_data(np.ones((10, 10)) + 1, data_label='twos')
        phot_plugin._on_viewer_data_changed()
        phot_plugin.data_selected = 'twos'
        assert_allclose(phot_plugin.background_value, 2)  # Recalculate based on new Data


class TestSimpleAperPhot_NoWCS(BaseImviz_WCS_NoWCS):
    def test_plugin_no_wcs(self):
        # Most things already tested above, so not re-tested here.
        self.imviz._apply_interactive_region('bqplot:circle', (0, 0), (9, 9))  # Draw a circle
        phot_plugin = SimpleAperturePhotometry(app=self.imviz.app)
        phot_plugin._on_viewer_data_changed()

        phot_plugin.data_selected = 'has_wcs[SCI,1]'
        phot_plugin.subset_selected = 'Subset 1'
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 1

        phot_plugin.data_selected = 'no_wcs[SCI,1]'
        phot_plugin.vue_do_aper_phot()
        tbl = self.imviz.get_aperture_photometry_results()
        assert len(tbl) == 1  # Old table discarded due to incompatible column
        assert_array_equal(tbl['sky_center'], None)
