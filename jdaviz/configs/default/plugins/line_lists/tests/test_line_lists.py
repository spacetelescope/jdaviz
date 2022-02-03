import numpy as np

import astropy.units as u
from astropy.table import QTable
from jdaviz import Specviz
from jdaviz.configs.default.plugins.line_lists import line_lists
from specutils import Spectrum1D


def test_line_lists():
    viz = Specviz()
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


def test_redshift(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    # test that helper functions run, we'll test functionality at the plugin level
    specviz_helper.set_redshift(0.1)
    specviz_helper.set_redshift_slider_bounds(range=0.5, step=0.01)
    specviz_helper.set_redshift_slider_bounds(range='auto', step='auto')

    ll_plugin = line_lists.LineListTool(app=specviz_helper.app)
    ll_plugin.rs_redshift = 0.1
    assert ll_plugin.rs_rv == 28487.06614479641

    ll_plugin.rs_rv = 30000
    assert ll_plugin.rs_redshift == 0.10561890816244568
