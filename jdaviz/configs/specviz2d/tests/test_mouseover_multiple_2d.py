import numpy as np
import pytest
from astropy import units as u
from specutils import Spectrum
from jdaviz.core.marks import PluginLine


@pytest.mark.xfail(reason="Currently fails due to UnitConversionError with pixel units")
def test_multiple_2d_spectra(deconfigged_helper, spectrum2d, mos_spectrum2d):
    """
    Test mouseover handling for multiple 2D spectra with different wavelength mappings.

    This test module covers the scenario where multiple 2D spectra are loaded with:
    - WCS-based wavelength mapping (using astropy WCS)
    - Simple spectral axis-based wavelength mapping
    - No wavelength mapping (pixel coordinates only)

    Mouseover previews should appear on all relevant viewers.
    """
    def _mouseover_and_check_line_visible(viewer, label_mouseover, x, y):
        # Simulate mouseover event at a specific position
        label_mouseover._viewer_mouse_event(viewer,
                                            {'event': 'mousemove', 'domain': {'x': x, 'y': y}})
        line_visible = False
        for mark in viewer.figure.marks:
            if isinstance(mark, PluginLine) and mark.visible:
                line_visible = True
                break
        return line_visible

    deconfigged_helper.load(mos_spectrum2d, data_label='2D Spectrum WCS',
                            format='2D Spectrum')

    viewer_1d = deconfigged_helper.viewers['1D Spectrum']._obj.glue_viewer
    viewer_2d = deconfigged_helper.viewers['2D Spectrum']._obj.glue_viewer

    # Get the coordinates info object for mouseover
    label_mouseover = deconfigged_helper._coords_info

    # Test mouseover on 2D spectrum with WCS
    assert _mouseover_and_check_line_visible(viewer_2d, label_mouseover, 5, 5)
    # Test mouseover on 1d spectrum linked to the 2D spectrum
    assert _mouseover_and_check_line_visible(viewer_1d, label_mouseover, 5, 5)

    # Add a second 2D spectrum with simple spectral axis (no WCS)
    deconfigged_helper.load(spectrum2d, data_label='2D Spectrum Spectral Axis',
                            format='2D Spectrum')
    assert _mouseover_and_check_line_visible(viewer_2d, label_mouseover, 5, 5)
    assert _mouseover_and_check_line_visible(viewer_1d, label_mouseover, 5, 5)

    data_no_wcs = np.ones((12, 18)) * 2.0
    data_no_wcs[6] = np.arange(18) * 0.3
    # Create spectrum without spectral_axis or wcs - just pixel coordinates
    spectrum2d_no_wavelength = Spectrum(flux=data_no_wcs*u.Jy, spectral_axis_index=0)

    # TODO: fix failure 'astropy.units.errors.UnitConversionError: 'pix' and 'm' (length)
    #  are not convertible'
    deconfigged_helper.load(spectrum2d_no_wavelength, data_label='2D Spectrum No Wavelength',
                            format='2D Spectrum')
    assert _mouseover_and_check_line_visible(viewer_2d, label_mouseover, 5, 5)
    assert _mouseover_and_check_line_visible(viewer_1d, label_mouseover, 5, 5)
