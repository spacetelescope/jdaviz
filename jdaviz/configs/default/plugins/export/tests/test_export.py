import os
import re

import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData
from glue.core.edit_subset_mode import AndMode, NewMode
from glue.core.roi import CircularROI, XRangeROI
from regions import Regions, CircleSkyRegion
from specutils import Spectrum1D


@pytest.mark.usefixtures('_jail')
class TestExportSubsets:
    """
    Tests for exporting subsets. Currently limited to non-composite spatial
    subsets.
    """

    def test_basic_export_subsets_imviz(self, imviz_helper):

        data = NDData(np.ones((500, 500)) * u.nJy)

        imviz_helper.load_data(data)

        imviz_helper.app.get_viewer('imviz-0').apply_roi(CircularROI(xc=250,
                                                                     yc=250,
                                                                     radius=100))
        export_plugin = imviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_format.selected == 'fits'  # default format
        assert export_plugin.subset_invalid_msg == ''  # for non-composite spatial

        export_plugin.export()
        assert os.path.isfile('imviz_export.fits')

        # read exported file back in
        with fits.open('imviz_export.fits') as hdu:
            fits_region = hdu[1].data[0]

        assert fits_region[0] == 'circle'
        assert fits_region[1] == fits_region[2] == 250.0
        assert fits_region[3] == 100.0
        assert fits_region[4] == 0.0

        # now test changing file format
        export_plugin.subset_format.selected = 'reg'
        export_plugin.export()
        assert os.path.isfile('imviz_export.reg')

        # read exported file back in
        region = Regions.read('imviz_export.reg')[0]
        assert region.center.x == 250.0
        assert region.center.y == 250.0
        assert region.radius == 100.0

        # changing file name
        export_plugin.filename = 'test'
        export_plugin.export()
        assert os.path.isfile('test.reg')

        # test that invalid file extension raises an error
        with pytest.raises(ValueError,
                           match=re.escape("x not one of ['fits', 'reg'], reverting selection to reg")):  # noqa
            export_plugin.subset_format.selected = 'x'

    def test_not_implemented(self, cubeviz_helper, spectral_cube_wcs):
        """
        Test that trying to export non-supported subsets
        (spectral and composite) produces
        the correct warning message to display in UI).
        """

        data = Spectrum1D(flux=np.ones((500, 500, 2)) * u.nJy,
                          wcs=spectral_cube_wcs)
        cubeviz_helper.load_data(data)

        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=255,
                                                                           yc=255,
                                                                           radius=50))
        cubeviz_helper.app.session.edit_subset_mode.mode = AndMode
        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=200,
                                                                           yc=250,
                                                                           radius=50))

        export_plugin = cubeviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_invalid_msg == 'Export for composite subsets not yet supported.'

        cubeviz_helper.app.session.edit_subset_mode.mode = NewMode
        cubeviz_helper.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(5, 15.5))
        assert 'Subset 2' not in export_plugin.subset.choices

    def test_export_subsets_wcs(self, imviz_helper, spectral_cube_wcs):

        # using cube WCS instead of 2d imaging wcs for consistancy with
        # cubeviz test. accessing just the spatial part of this.
        wcs = spectral_cube_wcs.celestial

        data = NDData(np.ones((500, 500)) * u.nJy, wcs=wcs)

        imviz_helper.load_data(data)  # load data twice so we can link them
        imviz_helper.load_data(data)

        imviz_helper.link_data(link_type='wcs')

        imviz_helper.app.get_viewer('imviz-0').apply_roi(CircularROI(xc=8,
                                                                     yc=6,
                                                                     radius=.2))

        export_plugin = imviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_invalid_msg == ''  # for non-composite spatial

        # test changing link type results in an output file with a sky region
        export_plugin.filename = 'sky_region'
        export_plugin.subset_format.selected = 'reg'
        export_plugin.export()

        assert os.path.isfile('sky_region.reg')

        assert isinstance(Regions.read('sky_region.reg')[0], CircleSkyRegion)

    def test_basic_export_subsets_cubeviz(self, cubeviz_helper, spectral_cube_wcs):

        data = Spectrum1D(flux=np.ones((128, 128, 256)) * u.nJy, wcs=spectral_cube_wcs)

        cubeviz_helper.load_data(data)

        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=50,
                                                                           yc=50,
                                                                           radius=10))

        export_plugin = cubeviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_format.selected == 'fits'  # default format

        export_plugin.export()
        assert os.path.isfile('cubeviz_export.fits')

        # read exported file back in
        with fits.open('cubeviz_export.fits') as hdu:
            fits_region = hdu[1].data[0]

        assert fits_region[0] == 'circle'
        assert fits_region[1] == fits_region[2] == 50.0
        assert fits_region[3] == 10.0
        assert fits_region[4] == 0.0

        # now test changing file format
        export_plugin.subset_format.selected = 'reg'
        export_plugin.export()
        assert os.path.isfile('cubeviz_export.reg')

        # read exported file back in
        region = Regions.read('cubeviz_export.reg')[0]
        assert region.center.x == 50.0
        assert region.center.y == 50.0
        assert region.radius == 10.0

        # changing file name
        export_plugin.filename = 'test'
        export_plugin.export()
        assert os.path.isfile('test.reg')

        # Overwrite not enable, so no-op with warning.
        export_plugin.export(raise_error_for_overwrite=False)
        assert export_plugin.overwrite_warn

        # Changing filename should clear warning.
        old_filename = export_plugin.filename
        export_plugin.filename = "foo"
        assert not export_plugin.overwrite_warn
        export_plugin.filename = old_filename

        # Overwrite not enable, but with exception from API by default.
        with pytest.raises(FileExistsError, match=".* exists but overwrite=False"):
            export_plugin.export()
        assert export_plugin.overwrite_warn

        # User forces overwrite.
        export_plugin.export(overwrite=True)
        assert not export_plugin.overwrite_warn

        # test that invalid file extension raises an error
        with pytest.raises(ValueError,
                           match=re.escape("x not one of ['fits', 'reg'], reverting selection to reg")):  # noqa
            export_plugin.subset_format.selected = 'x'

        # test that attempting to save a composite subset raises an error
        cubeviz_helper.app.session.edit_subset_mode.mode = AndMode
        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=25, yc=25, radius=5))
        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=20, yc=25, radius=5))

        with pytest.raises(NotImplementedError,
                           match='Subset can not be exported - Export for composite subsets not yet supported.'):  # noqa
            export_plugin.export()


@pytest.mark.usefixtures('_jail')
def test_export_data(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')
    mm = cubeviz_helper.plugins["Moment Maps"]
    mm.dataset = 'test[FLUX]'
    mm._obj.dataset_selected = 'test[FLUX]'
    mm.n_moment = 0
    mm.calculate_moment()
    assert mm._obj.results_label == 'moment 0'
    cubeviz_helper.app.add_data_to_viewer(
        cubeviz_helper._default_flux_viewer_reference_name, 'moment 0'
    )
    ep = cubeviz_helper.plugins["Export"]._obj
    assert 'test[FLUX]' not in ep.dataset.choices

    ep.dataset_selected = 'moment 0'
    assert ep.dataset_format.selected == 'fits'
    ep.export()
    assert os.path.isfile("cubeviz_export.fits")
    assert ep.data_invalid_msg == ''


def test_disable_export_for_unsupported_units(specviz2d_helper):
    dn_per_s = u.DN / u.s
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    data = Spectrum1D(flux=data*dn_per_s, spectral_axis=data[3]*u.um)
    specviz2d_helper.load_data(data)

    gs = specviz2d_helper.plugins["Gaussian Smooth"]
    smooth_source_dataset = "Spectrum 1D"
    gs.dataset = smooth_source_dataset
    gs.stddev = 3
    gs.smooth(add_data=True)

    ep = specviz2d_helper.plugins["Export"]._obj
    assert "Spectrum 1D smooth stddev-3.0" in ep.dataset.choices
    ep.dataset_selected = "Spectrum 1D smooth stddev-3.0"
    assert ep.dataset.selected_obj.unit == "DN/s"
    assert ep.data_invalid_msg == "Export Disabled: The unit DN / s could not be saved in native FITS format."  # noqa


class TestExportPluginPlots:

    def test_basic_export_plugin_plots(self, imviz_helper):
        """
        Test basic funcionality of exporting plugin plots
        from the export plugin. Tests on the 'Plot Options: stretch_hist'
        plot, which exists upon loading data, and also that plots that
        may have been initialized but are empty are not displayed in
        the Export plugin.
        """
        data = NDData(np.ones((500, 500)) * u.nJy)

        imviz_helper.load_data(data)

        export_plugin = imviz_helper.plugins['Export']._obj
        export_plugin.plugin_plot.selected = 'Plot Options: stretch_hist'

        assert export_plugin.plugin_plot_format.selected == 'png'  # should be default format
        # and change file type
        export_plugin.plugin_plot_format.selected = 'svg'

        export_plugin.filename == 'imviz_export'
        # change filename
        export_plugin.filename = 'test_export_plugin_plot'

        # just check that it doesn't crash, since we can't download
        export_plugin.export()

        # make sure that the only valid option for export is this plugin,
        # not the other plots that exist but are empty (ap phot and line profile)
        # this might change down the line if new plots are added.
        available_plots = [x['label'] for x in export_plugin.plugin_plot.items]
        assert len(available_plots) == 1
        assert available_plots[0] == 'Plot Options: stretch_hist'

    def test_ap_phot_plot_export(self, imviz_helper):

        """
        Test export functionality for plot from the aperture photometry
        plugin.
        """

        data = NDData(np.ones((500, 500)) * u.nJy)

        imviz_helper.load_data(data)

        export_plugin = imviz_helper.plugins['Export']._obj

        imviz_helper.app.get_viewer('imviz-0').apply_roi(CircularROI(xc=250,
                                                                     yc=250,
                                                                     radius=100))

        phot_plugin = imviz_helper.app.get_tray_item_from_name('imviz-aper-phot-simple')
        phot_plugin.aperture_selected = 'Subset 1'

        phot_plugin.vue_do_aper_phot()
        assert phot_plugin.plot_available

        available_plots = [x['label'] for x in export_plugin.plugin_plot.items]
        assert 'Aperture Photometry: plot' in available_plots

        export_plugin.plugin_plot.selected = 'Aperture Photometry: plot'

        # change filename
        export_plugin.filename = 'test_export_plugin_plot'
        # and change file type
        export_plugin.plugin_plot_format.selected = 'svg'

        # just check that it doesn't crash, since we can't download
        export_plugin.export()
