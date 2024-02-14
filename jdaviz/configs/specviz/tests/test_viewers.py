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
