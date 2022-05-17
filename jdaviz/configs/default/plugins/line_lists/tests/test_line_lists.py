import numpy as np
from numpy.testing import assert_allclose
import pytest

import astropy.units as u
from astropy.table import QTable
from jdaviz import Specviz
from specutils import Spectrum1D


def test_line_lists():
    viz = Specviz()
    spec = Spectrum1D(flux=np.random.rand(100)*u.Jy,
                      spectral_axis=np.arange(6000, 7000, 10)*u.AA)
    viz.load_spectrum(spec)

    lt = QTable()
    lt['linename'] = ['O III', 'Halpha']
    lt['rest'] = [0, 6563]*u.AA
    with pytest.raises(ValueError, match='all rest values must be positive'):
        viz.load_line_list(lt)

    lt = QTable()
    lt['linename'] = ['O III', 'Halpha']
    lt['rest'] = [5007, 6563]*u.AA
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

    lt = QTable()
    lt['linename'] = ['O III', 'Halpha']
    lt['rest'] = [5007, 6563]*u.AA
    lt['redshift'] = u.Quantity(0.046)
    lt['listname'] = 'Test List'
    with pytest.warns(UserWarning, match='per line/list redshifts not supported, use viz.set_redshift'):  # noqa
        specviz_helper.load_line_list(lt)

    ll_plugin = specviz_helper.app.get_tray_item_from_name('g-line-list')
    # fake the plugin to be opened so that all updates run
    ll_plugin.plugin_opened = True
    line = ll_plugin.list_contents['Test List']['lines'][0]
    assert_allclose(line['obs'], line['rest'])
    # test API access
    specviz_helper.set_redshift(0.01)
    specviz_helper.set_redshift_slider_bounds(range=0.5, step=0.01)
    specviz_helper.set_redshift_slider_bounds(range='auto', step='auto')

    # test plugin
    ll_plugin.rs_redshift = 0.1
    assert ll_plugin.rs_rv == 28487.06614479641

    ll_plugin.rs_rv = 30000
    assert ll_plugin.rs_redshift == 0.10561890816244568

    ll_plugin.vue_change_line_obs({'list_name': 'Test List',
                                   'line_ind': 0,
                                   'obs_new': 5508})
    assert_allclose(line['obs'], 5508)

    # https://github.com/spacetelescope/jdaviz/issues/1168
    ll_plugin.vue_set_identify(('Test List', line, 0))
    ll_plugin.vue_remove_list('Test List')
    assert ll_plugin._viewer.spectral_lines is None
    assert ll_plugin.identify_label == ''


def test_line_identify(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_spectrum(spectrum1d, data_label=label)

    lt = QTable()
    lt['linename'] = ['O III', 'Halpha']
    lt['rest'] = [5007, 6563]*u.AA
    lt['listname'] = 'Test List'
    specviz_helper.load_line_list(lt)

    ll_plugin = specviz_helper.app.get_tray_item_from_name('g-line-list')
    line = ll_plugin.list_contents['Test List']['lines'][0]
    assert line.get('identify', False) is False
    ll_plugin.vue_set_identify(('Test List', line, 0))
    assert line.get('identify', False) is True

    ll_plugin.vue_change_visible(('Test List', line, 0))
    assert line.get('show') is False
    assert line.get('identify', False) is False
