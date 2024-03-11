import astropy.units as u
import numpy as np
import pytest
from specutils import Spectrum1D


@pytest.mark.parametrize(
    ('input_unit', 'y_axis_label'),
    [(u.MJy, 'Flux density'),
     (u.MJy / u.sr, 'Surface brightness'),
     (u.electron / u.s, 'Counts'),
     (u.dimensionless_unscaled, 'Counts'),
     (u.erg / (u.s * u.cm ** 2), 'Flux'),
     (u.erg / u.s, 'Luminosity')])
def test_spectrum_viewer_axis_labels(specviz_helper, input_unit, y_axis_label):

    flux = np.arange(1, 10) * input_unit
    spectral_axis = np.arange(1, 10) * u.um

    spec = Spectrum1D(flux, spectral_axis)

    specviz_helper.load_data(spec)

    label = specviz_helper.app.get_viewer_by_id('specviz-0').figure.axes[1].label

    assert (y_axis_label in label)


class TestResetLimitsTwoTests:
    """See https://github.com/spacetelescope/lcviz/pull/93"""

    def test_reset_limits_01(self, specviz_helper, spectrum1d):
        """This should run first."""
        specviz_helper.load_data(spectrum1d)
        sv = specviz_helper.app.get_viewer("spectrum-viewer")

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
        sv = specviz_helper.app.get_viewer("spectrum-viewer")

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
