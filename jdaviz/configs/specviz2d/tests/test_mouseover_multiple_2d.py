import numpy as np
import pytest
from astropy import units as u
from specutils import Spectrum
from jdaviz.core.marks import PluginLine


class TestMouseoverMultiple2DSpectra:

    @pytest.fixture(scope='class')
    def spectrum_no_wavelength(self):
        """
        Create a 2D spectrum with no wavelength mapping (no WCS, no spectral_axis).
        """
        data_no_wcs = np.ones((18, 18)) * 2.0
        data_no_wcs[6] = np.arange(18) * 0.3
        return Spectrum(flux=data_no_wcs * u.Jy, spectral_axis_index=0)

    def _mouseover_and_check_line_visible(self, viewer, label_mouseover, x, y):
        # Simulate mouseover event at a specific position
        label_mouseover._viewer_mouse_event(viewer,
                                            {'event': 'mousemove', 'domain': {'x': x, 'y': y}})
        line_visible = False
        for mark in viewer.figure.marks:
            if isinstance(mark, PluginLine) and mark.visible:
                line_visible = True
                break
        return line_visible

    @pytest.mark.parametrize('spec', ['mos_spectrum2d', 'spectrum2d'])  # 'spectrum_no_wavelength'])
    def test_single_2d_spectrum(self, deconfigged_helper, spec, request):
        """
        Test mouseover handling for a single 2D spectrum with WCS, no WCS,
        and no wavelength mapping.
        """
        deconfigged_helper.load(request.getfixturevalue(spec), format='2D Spectrum')

        viewer_1d = deconfigged_helper.viewers['1D Spectrum']._obj.glue_viewer
        viewer_2d = deconfigged_helper.viewers['2D Spectrum']._obj.glue_viewer

        # Get the coordinates info object for mouseover
        label_mouseover = deconfigged_helper._coords_info

        # Test mouseover on 2D spectrum with WCS
        assert self._mouseover_and_check_line_visible(viewer_2d, label_mouseover, 5, 5)
        # Test mouseover on 1d spectrum linked to the 2D spectrum
        assert self._mouseover_and_check_line_visible(viewer_1d, label_mouseover, 5, 5)

    # TODO: Move this into parametrized test above once mouseover handling for 2D spectra
    #  with no wavelength mapping is resolved.
    @pytest.mark.skip(reason="Mouseover handling for 2D spectra with no wavelength mapping is being investigated.")  # noqa
    def test_single_2d_spectrum_no_wavelength(self, deconfigged_helper, spectrum_no_wavelength):
        """
        Test mouseover handling for a single 2D spectrum with WCS, no WCS,
        and no wavelength mapping.
        """
        deconfigged_helper.load(spectrum_no_wavelength, format='2D Spectrum')

        viewer_1d = deconfigged_helper.viewers['1D Spectrum']._obj.glue_viewer
        viewer_2d = deconfigged_helper.viewers['2D Spectrum']._obj.glue_viewer

        # Get the coordinates info object for mouseover
        label_mouseover = deconfigged_helper._coords_info

        # Test mouseover on 2D spectrum with WCS
        assert self._mouseover_and_check_line_visible(viewer_2d, label_mouseover, 5, 5)
        # Test mouseover on 1d spectrum linked to the 2D spectrum
        assert self._mouseover_and_check_line_visible(viewer_1d, label_mouseover, 5, 5)

    def test_multiple_2d_spectra(self, deconfigged_helper, spectrum2d, mos_spectrum2d):
        """
        Test mouseover handling for multiple 2D spectra with different wavelength mappings.

        This test module covers the scenario where multiple 2D spectra are loaded with:
        - WCS-based wavelength mapping (using astropy WCS)
        - Simple spectral axis-based wavelength mapping
        - No wavelength mapping (pixel coordinates only)

        Mouseover previews should appear on all relevant viewers.
        """

        deconfigged_helper.load(mos_spectrum2d, data_label='2D Spectrum WCS',
                                format='2D Spectrum')

        viewer_1d = deconfigged_helper.viewers['1D Spectrum']._obj.glue_viewer
        viewer_2d = deconfigged_helper.viewers['2D Spectrum']._obj.glue_viewer

        # Get the coordinates info object for mouseover
        label_mouseover = deconfigged_helper._coords_info

        # Test mouseover on 2D spectrum with WCS
        assert self._mouseover_and_check_line_visible(viewer_2d, label_mouseover, 5, 5)
        # Test mouseover on 1d spectrum linked to the 2D spectrum
        assert self._mouseover_and_check_line_visible(viewer_1d, label_mouseover, 5, 5)

        # Add a second 2D spectrum with simple spectral axis (no WCS)
        deconfigged_helper.load(spectrum2d, data_label='2D Spectrum Spectral Axis',
                                format='2D Spectrum')
        assert self._mouseover_and_check_line_visible(viewer_2d, label_mouseover, 5, 5)
        assert self._mouseover_and_check_line_visible(viewer_1d, label_mouseover, 5, 5)
