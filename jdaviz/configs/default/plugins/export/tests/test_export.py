import os
import re

import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData
from glue.core.roi import CircularROI, EllipticalROI
from regions import Regions, CircleSkyRegion
from specutils import Spectrum, SpectralRegion
from pathlib import Path
from astropy.wcs import WCS


@pytest.mark.usefixtures('_jail')
class TestExportSubsets:
    """
    Tests for exporting subsets. Currently limited to non-composite spatial
    subsets.
    """

    def test_basic_export_subsets_imviz(self, imviz_helper):

        data = NDData(np.ones((500, 500)) * u.nJy)

        imviz_helper.load_data(data)
        subset_plugin = imviz_helper.plugins['Subset Tools']
        subset_plugin.import_region(CircularROI(xc=250, yc=250, radius=100))

        export_plugin = imviz_helper.plugins['Export']._obj

        # Check initialization of these two
        assert export_plugin.subset_invalid_msg == ''
        assert export_plugin.subset_format_invalid_msg == ''

        export_plugin.subset.selected = 'Subset 1'

        # Make no assumptions on default since the 'default' is now
        # set by the first option in the list of available formats
        # (but it's *almost* 100% likely to be fits)
        spatial_valid_formats = ['fits', 'reg']
        assert export_plugin.subset_format.selected in spatial_valid_formats

        for current_format in spatial_valid_formats:
            export_plugin.subset_format.selected = current_format
            assert export_plugin.subset_format.selected == current_format
            assert export_plugin.subset_invalid_msg == ''  # for non-composite spatial
            assert export_plugin.subset_format_invalid_msg == ''

            assert export_plugin.filename.value.endswith(f".{current_format}")
            export_plugin.export()
            assert os.path.isfile(export_plugin.filename.value)

            # changing file name and catching the result (the new filename/path)
            # for checking the file
            new_filename = 'test'
            export_plugin.filename.value = new_filename
            output_filename = export_plugin.export()
            assert os.path.isfile(f'{new_filename}.{current_format}')
            assert os.path.isfile(output_filename)

            if current_format == 'fits':
                # read exported file back in
                with fits.open(output_filename) as hdu:
                    fits_region = hdu[1].data[0]

                assert fits_region[0] == 'circle'
                assert fits_region[1] == fits_region[2] == 250.0
                assert fits_region[3] == 100.0
                assert fits_region[4] == 0.0

            elif current_format == 'reg':
                # read exported file back in
                region = Regions.read(output_filename)[0]
                assert region.center.x == 250.0
                assert region.center.y == 250.0
                assert region.radius == 100.0

        # test that invalid file extension raises an error
        with pytest.raises(ValueError,
                           match=re.escape("'x' not one of ['fits', 'reg', 'ecsv'], reverting selection to 'reg'")):  # noqa
            export_plugin.subset_format.selected = 'x'

    def test_not_implemented(self, cubeviz_helper, spectral_cube_wcs):
        """
        Test that trying to export non-supported subsets
        (spectral and composite) produces
        the correct warning message to display in UI).
        """

        data = Spectrum(flux=np.ones((500, 500, 2)) * u.nJy,
                        wcs=spectral_cube_wcs)
        cubeviz_helper.load_data(data)
        subset_plugin = cubeviz_helper.plugins['Subset Tools']
        subset_plugin.import_region(CircularROI(xc=255, yc=255, radius=50))
        subset_plugin.import_region(CircularROI(xc=200, yc=250, radius=50), edit_subset='Subset 1',
                                    combination_mode='and')

        export_plugin = cubeviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_invalid_msg == 'Export for composite subsets not yet supported.'

    def test_export_subsets_wcs(self, imviz_helper, spectral_cube_wcs):

        # using cube WCS instead of 2d imaging wcs for consistency with
        # cubeviz test. accessing just the spatial part of this.
        wcs = spectral_cube_wcs.celestial

        data = NDData(np.ones((500, 500)) * u.nJy, wcs=wcs)

        imviz_helper.load_data(data)  # load data twice so we can link them
        imviz_helper.load_data(data)

        imviz_helper.link_data(align_by='wcs')
        subset_plugin = imviz_helper.plugins['Subset Tools']
        subset_plugin.import_region(CircularROI(xc=8, yc=6, radius=.2))

        export_plugin = imviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_invalid_msg == ''  # for non-composite spatial

        # test changing link type results in an output file with a sky region
        export_plugin.subset_format.selected = 'reg'
        export_plugin.filename_value = 'sky_region.reg'
        export_plugin.export()

        assert os.path.isfile('sky_region.reg')

        assert isinstance(Regions.read('sky_region.reg')[0], CircleSkyRegion)

    def test_basic_export_subsets_cubeviz(self, cubeviz_helper, spectral_cube_wcs):

        data = Spectrum(flux=np.ones((128, 128, 256)) * u.nJy, wcs=spectral_cube_wcs)

        # Subset 1, Spatial Subset
        cubeviz_helper.load_data(data)
        subset_plugin = cubeviz_helper.plugins['Subset Tools']
        subset_plugin.import_region(CircularROI(xc=50, yc=50, radius=10))

        # Subset 2, Spectral Subset
        spectral_axis_unit = u.Unit(
            cubeviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
        subset_plugin.import_region(SpectralRegion(5 * spectral_axis_unit,
                                                   15.5 * spectral_axis_unit))

        export_plugin = cubeviz_helper.plugins['Export']._obj

        # Assert that the default name is set and that they're in order
        # Mostly to confirm the use of spatial/specctral_subset variables
        assert export_plugin.subset.choices[0] == 'Subset 1'
        spatial_subset = 'Subset 1'

        assert export_plugin.subset.choices[1] == 'Subset 2'
        spectral_subset = 'Subset 2'

        # No subset is selected by default
        assert export_plugin.subset.selected == ''

        export_plugin.subset.selected = spatial_subset
        spatial_valid_formats = ['fits', 'reg']
        # Assert that the first subset created has the first format available (fits).
        assert export_plugin.subset_format.selected in spatial_valid_formats

        for current_format in spatial_valid_formats:
            # Check that the format and filename are set correctly
            export_plugin.subset_format.selected = current_format
            assert export_plugin.subset_format.selected == current_format
            assert export_plugin.filename.value.endswith(current_format)

            assert export_plugin.subset_invalid_msg == ''  # for non-composite spatial
            assert export_plugin.subset_format_invalid_msg == ''

            # Attempt export
            export_plugin.export()
            assert os.path.isfile(export_plugin.filename.value)

            # changing file name and catching the result (the new filename/path)
            # for checking the file
            new_filename = 'test'
            export_plugin.filename.value = new_filename
            output_filename = export_plugin.export()
            assert os.path.isfile(f'{new_filename}.{current_format}')
            assert os.path.isfile(output_filename)

            if current_format == 'fits':
                # read exported file back in
                with fits.open(output_filename) as hdu:
                    fits_region = hdu[1].data[0]

                assert fits_region[0] == 'circle'
                assert fits_region[1] == fits_region[2] == 50.0
                assert fits_region[3] == 10.0
                assert fits_region[4] == 0.0

            elif current_format == 'reg':
                # read exported file back in
                region = Regions.read(output_filename)[0]
                assert region.center.x == 50.0
                assert region.center.y == 50.0
                assert region.radius == 10.0

            # Finally, attempt to export with Spectral subset
            export_plugin.subset.selected = spectral_subset
            # subset_format_invalid_msg should already be populated since
            # the selected format is fits/reg
            assert export_plugin.subset_format_invalid_msg != ''
            with pytest.raises(ValueError,
                               match=f"Export of '{spectral_subset}' "
                                       f"in '{current_format}' format is not supported."):  # noqa
                export_plugin.export()

            # Reset to spatial
            export_plugin.subset.selected = spatial_subset

        # Overwrite not enable, so no-op with warning.
        export_plugin.export(raise_error_for_overwrite=False)
        assert export_plugin.overwrite_warn

        # Changing filename should clear warning.
        old_filename = export_plugin.filename_value
        export_plugin.filename_value = "foo"
        assert not export_plugin.overwrite_warn
        export_plugin.filename_value = old_filename

        # Overwrite not enable, but with exception from API by default.
        with pytest.raises(FileExistsError, match=".* exists but overwrite=False"):
            export_plugin.export()
        assert export_plugin.overwrite_warn

        # User forces overwrite.
        export_plugin.export(overwrite=True)
        assert not export_plugin.overwrite_warn

        # test that invalid file extension raises an error
        with pytest.raises(ValueError,
                           match=re.escape(
                               "'x' not one of ['fits', 'reg', 'ecsv'], reverting selection to 'reg'")):  # noqa
            export_plugin.subset_format.selected = 'x'

        # Test that attempting to export with disabled option raises an error
        export_plugin.subset_format.selected = 'ecsv'
        with pytest.raises(ValueError,
                           match=f"Export of '{spatial_subset}' "
                                 f"in 'ecsv' format is not supported."):  # noqa
            export_plugin.export()

        # test that attempting to save a composite subset raises an error
        subset_plugin.import_region(CircularROI(xc=25, yc=25, radius=5), edit_subset='Subset 1',
                                    combination_mode='and')
        subset_plugin.import_region(CircularROI(xc=20, yc=25, radius=5), edit_subset='Subset 1',
                                    combination_mode='and')

        export_plugin.subset.selected = spatial_subset
        # A user *must* (re)select the subset for the subset_invalid_msg to be filled
        # if the subset is already selected and subsequently edited, the message
        # will be an empty string
        assert export_plugin.subset_invalid_msg == 'Export for composite subsets not yet supported.'
        # However it *will* still fail on export.
        with pytest.raises(NotImplementedError,
                           match='Subset cannot be exported - Export for composite subsets not yet supported.'):  # noqa
            export_plugin.export()

        export_plugin.subset.selected = spectral_subset
        export_plugin.filename_value = "test_spectral_region"
        export_plugin.export()
        assert os.path.isfile('test_spectral_region.ecsv')

        # Revert spectral subset format selection to fits and check
        # that the format message is populated
        export_plugin.subset_format.selected = 'fits'
        assert export_plugin.subset_format_invalid_msg != ''
        # Delete the spectral subset and check that the message is reset
        cubeviz_helper.app.delete_subsets(spectral_subset)
        assert export_plugin.subset_format_invalid_msg == ''

    def test_export_stcs_circle_ellipse(self, imviz_helper):
        wcs = WCS({'CTYPE1': 'RA---TAN', 'CUNIT1': 'deg', 'CDELT1': -0.0002777777778,
                   'CRPIX1': 1, 'CRVAL1': 9.423508457380343,
                   'CTYPE2': 'DEC--TAN', 'CUNIT2': 'deg', 'CDELT2': 0.0002777777778,
                   'CRPIX2': 1, 'CRVAL2': -33.71313112382379})
        arr = np.arange(40000).reshape(200, 200)
        ndd = NDData(arr, wcs=wcs)
        imviz_helper.load_data(ndd)
        imviz_helper.link_data(align_by='wcs')

        subset_plugin = imviz_helper.plugins['Subset Tools']
        export_plugin = imviz_helper.plugins['Export']._obj

        subset_plugin.import_region(CircularROI(xc=40, yc=50, radius=10))
        export_plugin.subset.selected = 'Subset 1'
        export_plugin.subset_format.selected = 'stcs'
        export_plugin.filename_value = 'Subset_1.stcs'
        export_plugin.export()
        with open('Subset_1.stcs') as f:
            contents = f.read().split()
        assert contents[0] == 'CIRCLE'
        assert contents[1] == 'ICRS'
        assert contents[2] == '9.157221'
        assert contents[3] == '-33.435070'
        assert contents[4] == '0.055554'

        subset_plugin.import_region(EllipticalROI(xc=45, yc=55, radius_x=8, radius_y=4, theta=0.2))
        export_plugin.subset.selected = 'Subset 2'
        export_plugin.subset_format.selected = 'stcs'
        export_plugin.filename_value = 'Subset_2.stcs'
        export_plugin.export(overwrite=True)
        with open('Subset_2.stcs') as f:
            contents = f.read().split()
        assert contents[0] == 'ELLIPSE'
        assert contents[1] == 'ICRS'
        assert contents[2] == '9.124032'
        assert contents[3] == '-33.407217'
        assert contents[4] == '0.088886'
        assert contents[5] == '0.044443'
        assert contents[6] == '11.625269'


@pytest.mark.usefixtures('_jail')
def test_export_cubeviz_spectrum_viewer(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    ep = cubeviz_helper.plugins["Export"]
    ep.viewer = 'spectrum-viewer'
    ep.viewer_format = 'png'
    ep.export()

    ep.viewer_format = 'svg'
    ep.export()


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
    assert os.path.isfile(ep.filename.value)
    assert ep.data_invalid_msg == ''


def test_disable_export_for_unsupported_units(specviz2d_helper):
    dn_per_s = u.DN / u.s
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    data = Spectrum(flux=data*dn_per_s, spectral_axis=data[3]*u.um)
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

        assert export_plugin.filename.value.endswith('.svg')
        # change filename
        export_plugin.filename_value = 'test_export_plugin_plot'

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
        subset_plugin = imviz_helper.plugins['Subset Tools']
        subset_plugin.import_region(CircularROI(xc=250, yc=250, radius=100))

        phot_plugin = imviz_helper.app.get_tray_item_from_name('imviz-aper-phot-simple')
        phot_plugin.aperture_selected = 'Subset 1'

        phot_plugin.vue_do_aper_phot()
        assert phot_plugin.plot_available

        available_plots = [x['label'] for x in export_plugin.plugin_plot.items]
        assert 'Aperture Photometry: plot' in available_plots

        export_plugin.plugin_plot.selected = 'Aperture Photometry: plot'

        # change filename
        export_plugin.filename_value = 'test_export_plugin_plot'
        # and change file type
        export_plugin.plugin_plot_format.selected = 'svg'

        # just check that it doesn't crash, since we can't download
        export_plugin.export()

    def test_figure_export(self, imviz_helper):

        data = NDData(np.ones((500, 500)) * u.nJy)

        imviz_helper.load_data(data)

        export_plugin = imviz_helper.plugins['Export']._obj

        export_plugin.export(filename=None)

        # attempt to save a figure back to back
        try:
            export_plugin.export(filename='img.png')
        except ValueError as e:
            assert str(e) == "previous png export is still in progress. Wait to complete before making another call to save_figure"  # noqa: E501

    def test_filepath_convention(self, imviz_helper):
        data = NDData(np.ones((500, 500)) * u.nJy)
        imviz_helper.load_data(data)
        export_plugin = imviz_helper.plugins['Export']._obj

        # Set filename value using OS-independent Path methods
        export_plugin.filename_value = str(Path('/') / 'img.png')
        assert os.path.abspath(export_plugin.default_filepath) == os.path.abspath(export_plugin.filename_value)  # noqa: E501

        export_plugin.filename_value = str(Path('~') / 'img.png')
        expected_path = str(Path('~').expanduser() / 'img.png')
        assert export_plugin.default_filepath == expected_path

        export_plugin.filename_value = str(Path('..') / 'img.png')
        expected_path = str((Path('..') / 'img.png').resolve())
        assert export_plugin.default_filepath == expected_path

        export_plugin.filename_value = str(Path('.') / 'img.png')
        expected_path = str((Path('.') / 'img.png').resolve())
        assert export_plugin.default_filepath == expected_path
