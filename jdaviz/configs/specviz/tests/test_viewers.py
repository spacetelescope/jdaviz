import astropy.units as u
import numpy as np
import pytest
import warnings
from specutils import Spectrum


@pytest.mark.parametrize(
    ('input_unit', 'y_axis_label'),
    [(u.MJy, 'Flux'),
     (u.MJy / u.sr, 'Surface Brightness'),
     (u.electron / u.s, 'Counts'),
     (u.dimensionless_unscaled, 'Counts'),
     (u.erg / (u.s * u.cm ** 2), 'Flux'),
     (u.erg / u.s, 'Luminosity')])
def test_spectrum_viewer_axis_labels(specviz_helper, input_unit, y_axis_label):

    flux = np.arange(1, 10) * input_unit
    spectral_axis = np.arange(1, 10) * u.um

    spec = Spectrum(flux, spectral_axis)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*contains multiple slashes, which is discouraged by the FITS standard.*")  # noqa
        specviz_helper.load_data(spec)

    label = specviz_helper._spectrum_viewer.figure.axes[1].label

    assert (y_axis_label in label)


def test_spectrum_viewer_keep_unit_when_removed(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="Test")
    uc = specviz_helper.plugins["Unit Conversion"]
    assert uc.flux_unit == "Jy"
    uc.flux_unit = "MJy"
    specviz_helper.app.remove_data_from_viewer('spectrum-viewer', "Test")
    specviz_helper.app.add_data_to_viewer('spectrum-viewer', "Test")
    # Actual values not in display unit but should not affect display unit.
    spec = specviz_helper.get_spectra(data_label="Test", apply_slider_redshift=False)
    assert spec.flux.unit == u.Jy
    assert uc.flux_unit.selected == "MJy"
    assert specviz_helper.app._get_display_unit('spectral_y') == "MJy"


def test_limits_on_unit_change(specviz_helper, spectrum1d):
    """
    Test that the x-limits are reset when changing units
    """
    specviz_helper.load_data(spectrum1d, data_label="Test")
    uc = specviz_helper.plugins["Unit Conversion"]
    sv = specviz_helper.viewers['spectrum-viewer']

    assert uc.spectral_unit == "Angstrom"
    assert np.allclose(sv._obj.get_limits(), (6000.0, 8000.0,
                                              12.30618014327326, 16.542560043585965))

    uc.spectral_unit = 'Ci'
    assert np.allclose(sv._obj.get_limits(), (10128.0, 13504.164774774774,
                                              12.30618014327326, 16.542560043585965))

    uc.spectral_unit = 'erg'
    assert np.allclose(sv._obj.get_limits(), (2.4830270237304e-12, 3.3107430952482144e-12,
                                              12.30618014327326, 16.542560043585965))


class TestResetLimitsTwoTests:
    """See https://github.com/spacetelescope/lcviz/pull/93"""

    def test_reset_limits_01(self, specviz_helper, spectrum1d):
        """This should run first."""
        specviz_helper.load_data(spectrum1d)
        sv = specviz_helper.app.get_viewer('spectrum-viewer')

        orig_xlims = (sv.state.x_min, sv.state.x_max)
        orig_ylims = (sv.state.y_min, sv.state.y_max)
        # set xmin and ymin to midpoints
        new_xmin = (sv.state.x_min + sv.state.x_max) * 0.5
        new_ymin = (sv.state.y_min + sv.state.y_max) * 0.5
        sv.state.x_min = new_xmin
        sv.state.y_min = new_ymin

        sv.state._reset_x_limits()
        assert sv.state.x_min == orig_xlims[0]
        assert sv.state.y_min == new_ymin

        sv.state._reset_y_limits()
        assert sv.state.y_min == orig_ylims[0]

    def test_reset_limits_02(self, specviz_helper, spectrum1d_nm):
        """This should run second and see if first polutes it."""
        specviz_helper.load_data(spectrum1d_nm)
        sv = specviz_helper.app.get_viewer('spectrum-viewer')

        orig_xlims = (sv.state.x_min, sv.state.x_max)
        orig_ylims = (sv.state.y_min, sv.state.y_max)
        # set xmin and ymin to midpoints
        new_xmin = (sv.state.x_min + sv.state.x_max) * 0.5
        new_ymin = (sv.state.y_min + sv.state.y_max) * 0.5
        sv.state.x_min = new_xmin
        sv.state.y_min = new_ymin

        sv.state._reset_x_limits()
        assert sv.state.x_min == orig_xlims[0]
        assert sv.state.y_min == new_ymin

        sv.state._reset_y_limits()
        assert sv.state.y_min == orig_ylims[0]
