import numpy as np

import astropy.units as u
from astropy.table import QTable
from jdaviz import SpecViz
from specutils import Spectrum1D


def test_line_lists():
    viz = SpecViz()
    spec = Spectrum1D(flux=np.random.rand(100)*u.Jy,
                      spectral_axis=np.arange(6000, 7000, 10)*u.AA)
    viz.load_spectrum(spec)

    lt = QTable()
    lt['linename'] = ['O III', 'Halpha']
    lt['rest'] = [5007, 6563]*u.AA
    lt['redshift'] = u.Quantity(0.046)
    viz.load_line_list(lt)

    assert len(viz.spectral_lines) == 2
    assert viz.spectral_lines.loc["linename", "Halpha"]["listname"] == "Custom"
    assert np.all(viz.spectral_lines["show"])

    viz.erase_spectral_lines()

    assert np.all(viz.spectral_lines["show"] == False)  # noqa

    viz.plot_spectral_line("Halpha")
    viz.plot_spectral_line("O III 5007.0")

    assert np.all(viz.spectral_lines["show"])
