import astropy.units as u
import numpy as np
from astropy.table import QTable
from glue.core import Data
from glue.core.message import ComponentsChangedMessage
from numpy.testing import assert_allclose


def test_spectral_lines_relevancy(deconfigged_helper, spectrum1d, image_nddata_wcs):

    deconfigged_helper._app.state.dev_spectral_lines_plugin = True

    # 'plugins' dict only exposes relevant plugins, so fetch from tray directly
    plugin = deconfigged_helper._app.get_tray_item_from_name('g-spectral-lines')

    # no spectrum viewer yet, plugin should be irrelevant and not in the API
    assert plugin.irrelevant_msg != ''
    assert 'Spectral Lines' not in deconfigged_helper.plugins

    # load a spectrum (creates the 1D Spectrum viewer), plugin should be relevant
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='my_spec')
    assert plugin.irrelevant_msg == ''
    assert 'Spectral Lines' in deconfigged_helper.plugins

    # remove the spectrum, plugin should be irrelevant again
    deconfigged_helper._app.data_item_remove('my_spec')
    assert plugin.irrelevant_msg != ''
    assert 'Spectral Lines' not in deconfigged_helper.plugins

    # loading a non-spectrum (image) should not make the plugin relevant
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='my_image')
    assert plugin.irrelevant_msg != ''
    assert 'Spectral Lines' not in deconfigged_helper.plugins


def test_spectral_lines_relevancy_table_viewer(deconfigged_helper):

    deconfigged_helper._app.state.dev_spectral_lines_plugin = True

    plugin = deconfigged_helper._app.get_tray_item_from_name('g-spectral-lines')

    # no viewers at all yet, plugin should be irrelevant
    assert plugin.irrelevant_msg != ''

    # load a line list into a table viewer (no spectrum viewer involved)
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'wavelength': [6562.8, 7000.0] * u.AA, 'name': ['Ha', 'line2']})
    ldr.format = 'Spectral Lines'
    importer = ldr.importer
    importer.viewer.create_new = 'Spectral Line Table'
    importer()

    # a spectral line listtable viewer showing should make the plugin relevant
    assert 'Spectral Line Table' in deconfigged_helper.viewers
    assert plugin.irrelevant_msg == ''

    # removing the table viewer's data should make it irrelevant again
    deconfigged_helper._app.data_item_remove(deconfigged_helper._app.data_collection[0].label)
    assert plugin.irrelevant_msg != ''


def test_spectral_lines_uses_loader_linename_col(deconfigged_helper, spectrum1d):
    """
    component_lines should read line names from the column set in
    ``_jdaviz_loader_linename_col``, so they're displayed in the UI."""

    deconfigged_helper._app.state.dev_spectral_lines_plugin = True
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='my_spec')
    plugin = deconfigged_helper._app.get_tray_item_from_name('g-spectral-lines')

    rest_wav = np.array([6562.8, 7000.0])
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'wavelength': rest_wav * u.AA,
                         'designation': ['Ha', 'line2']})
    ldr.format = 'Spectral Lines'
    importer = ldr.importer

    # not auto-detected as the line-name column since it doesn't match any
    # of the known naming patterns
    assert importer._obj.linename_selected == '---'
    importer._obj.linename_selected = 'designation'
    importer()

    line_data = deconfigged_helper._app.data_collection[plugin.line_table]
    assert line_data.meta['_jdaviz_loader_linename_col'] == 'designation'


def test_spectral_lines_components(deconfigged_helper, spectrum1d):

    deconfigged_helper._app.state.dev_spectral_lines_plugin = True

    # load a spectrum1d that spans 6000-8000 angstrom
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='my_spec')

    # 'plugins' dict only exposes relevant plugins, so fetch from tray directly
    plugin = deconfigged_helper._app.get_tray_item_from_name('g-spectral-lines')

    # import a line list with lines in range of the loaded spectrum
    rest_wav = np.array([6562.8, 7000.0])
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'wavelength': rest_wav * u.AA, 'name': ['Ha', 'line2']})
    ldr.format = 'Spectral Lines'
    importer = ldr.importer
    importer.col_other = ['name']
    importer()

    # plugin picked up the table and added a column for the default component
    assert plugin.line_table != ''
    line_data = deconfigged_helper._app.data_collection[plugin.line_table]

    # and that it is correctly listed as a plugin-managed component column
    assert '_jdaviz_plugin_component_column' in line_data.meta
    assert 'observed wavelength:default' in line_data.meta['_jdaviz_plugin_component_column']

    # line names are read from the column recorded by the loader in meta
    assert line_data.meta['_jdaviz_loader_linename_col'] == 'name'

    def col(component_lbl):
        cid = plugin._get_data_component_id(line_data,
                                            f'observed wavelength:{component_lbl}')
        assert cid is not None
        return line_data[cid]

    def component_lines_field(field):
        return [line[field] for line in plugin.component_lines]

    assert plugin.component_selected == 'default'
    assert_allclose(col('default'), rest_wav)

    # component_lines reflects the names/rest/observed wavelengths of the
    # currently selected component, all initially visible
    assert component_lines_field('linename') == ['Ha', 'line2']
    assert_allclose(component_lines_field('rest'), rest_wav)
    assert_allclose(component_lines_field('obs'), rest_wav)
    assert component_lines_field('show') == [True, True]

    # a new component gets its own column, initially unshifted (z=0)
    plugin.component.add_choice('second')
    assert plugin.component_selected == 'second'
    assert plugin.component_redshift == 0
    assert_allclose(col('second'), rest_wav)
    assert_allclose(component_lines_field('obs'), rest_wav)

    # and that it is correctly listed as a plugin-managed component column
    assert 'observed wavelength:second' in line_data.meta['_jdaviz_plugin_component_column']

    # adjusting the redshift updates only the selected component's column
    # and its entries in component_lines
    plugin.component_redshift = 0.1
    assert_allclose(col('second'), rest_wav * 1.1)
    assert_allclose(col('default'), rest_wav)
    assert_allclose(component_lines_field('obs'), rest_wav * 1.1)
    assert_allclose(component_lines_field('rest'), rest_wav)

    # toggling visibility only affects the current component's display state
    plugin.vue_toggle_line_visibility(0)
    assert component_lines_field('show') == [False, True]

    # switching to another component keeps its own (unaffected) visibility...
    plugin.component_selected = 'default'
    assert component_lines_field('show') == [True, True]
    assert_allclose(component_lines_field('obs'), rest_wav)

    # ...and switching back restores the toggled state and redshifted values
    plugin.component_selected = 'second'
    assert component_lines_field('show') == [False, True]
    assert_allclose(component_lines_field('obs'), rest_wav * 1.1)

    # renaming moves the shifted column to the new name and keeps the redshift
    plugin.component.rename_choice('second', 'renamed')
    assert plugin._get_data_component_id(line_data, 'observed wavelength:second') is None
    assert_allclose(col('renamed'), rest_wav * 1.1)
    assert plugin.component_selected == 'renamed'
    assert plugin.component_redshift == 0.1

    # the plugin-managed component column should also reflect the rename
    assert 'observed wavelength:renamed' in line_data.meta['_jdaviz_plugin_component_column']
    assert 'observed wavelength:second' not in line_data.meta['_jdaviz_plugin_component_column']

    # component_lines follows the rename, keeping the shifted values and
    # per-line visibility state
    assert component_lines_field('linename') == ['Ha', 'line2']
    assert_allclose(component_lines_field('obs'), rest_wav * 1.1)
    assert component_lines_field('show') == [False, True]

    # removing a component removes its column, leaving others untouched
    plugin.component.remove_choice('renamed')
    assert plugin._get_data_component_id(line_data, 'observed wavelength:renamed') is None
    assert plugin.component_selected == 'default'
    assert plugin.component_redshift == 0
    assert_allclose(col('default'), rest_wav)

    # the plugin-managed component column should no longer include the removed component
    assert 'observed wavelength:renamed' not in line_data.meta['_jdaviz_plugin_component_column']

    # component_lines reflects the fallback to 'default', unshifted and visible
    assert_allclose(component_lines_field('obs'), rest_wav)
    assert component_lines_field('show') == [True, True]


def test_components_all_importer_tables(deconfigged_helper, monkeypatch):
    """Components are shared, but units and IDs remain local to each source."""
    from jdaviz.core import spectral_line_layers

    app = deconfigged_helper._app
    plugin = app.get_tray_item_from_name('g-spectral-lines')
    sync_calls = []
    rename_calls = []

    def sync(app_arg, source, create=False):
        assert app_arg is app
        assert create is False
        sync_calls.append(source)

    def rename(app_arg, old, new):
        assert app_arg is app
        assert plugin._renaming_component
        # Projection rename precedes every original-column rename.
        for source in plugin._line_table_data():
            assert plugin._get_data_component_id(source, plugin._component_col_name(old))
            assert plugin._get_data_component_id(source, plugin._component_col_name(new)) is None
        rename_calls.append((old, new))

    # Isolate the plugin/helper contract; the helper's projection lifecycle is
    # tested separately from these real Glue source-table mutations.
    monkeypatch.setattr(spectral_line_layers, 'sync_spectral_line_components', sync,
                        raising=False)
    monkeypatch.setattr(spectral_line_layers, 'rename_spectral_line_component', rename,
                        raising=False)

    def load_lines(values, unit):
        loader = deconfigged_helper.loaders['object']
        loader.object = QTable({'wavelength': values * unit, 'name': ['one', 'two']})
        loader.format = 'Spectral Lines'
        loader.importer()
        return app.data_collection[plugin.line_table]

    first = load_lines(np.array([6500., 7000.]), u.AA)
    second = load_lines(np.array([500., 600.]), u.nm)
    auxiliary = Data(label='auxiliary', wavelength=[1., 2.])
    auxiliary.meta['_jdaviz_loader_spectral_loc_col'] = 'wavelength'
    app.data_collection.append(auxiliary)
    sync_calls.clear()

    plugin.component.add_choice('second')
    plugin.component_redshift = 0.1
    third = load_lines(np.array([1., 2.]), u.um)
    tables = [first, second, third]
    ids = [plugin._get_data_component_id(data, 'observed wavelength:second')
           for data in tables]
    assert len({id(cid) for cid in ids}) == 3

    def check_columns(label, redshift):
        for data, cid in zip(tables, ids):
            assert plugin._get_data_component_id(data, plugin._component_col_name(label)) is cid
            source = plugin._get_data_component_id(data, 'wavelength')
            assert_allclose(data[cid], data[source] * (1 + redshift))
            assert data.get_component(cid).units == data.get_component(source).units
            assert cid.parent is data
            assert plugin._component_col_name(label) in data.meta['_jdaviz_plugin_component_column']
            assert_allclose(data['observed wavelength:default'], data[source])

    check_columns('second', 0.1)
    plugin.component_redshift = 0.2
    check_columns('second', 0.2)
    assert plugin.line_table == third.label
    assert_allclose([line['rest'] for line in plugin.component_lines], [1., 2.])
    assert_allclose([line['obs'] for line in plugin.component_lines], [1.2, 2.4])

    sync_calls.clear()
    plugin.component.rename_choice('second', 'renamed')
    assert rename_calls == [('second', 'renamed')]
    assert len(sync_calls) == 3
    assert all(actual is expected for actual, expected in zip(sync_calls, tables))
    check_columns('renamed', 0.2)
    for data in tables:
        assert plugin._get_data_component_id(data, 'observed wavelength:second') is None
        assert 'observed wavelength:second' not in data.meta['_jdaviz_plugin_component_column']

    # Both kinds of Glue changes sync only original sources, never auxiliaries.
    sync_calls.clear()
    first.update_components({ids[0]: first[ids[0]] + 1})
    app.hub.broadcast(ComponentsChangedMessage(second))
    auxiliary.update_components({auxiliary.id['wavelength']: [3., 4.]})
    app.hub.broadcast(ComponentsChangedMessage(auxiliary))
    assert len(sync_calls) == 2
    assert sync_calls[0] is first
    assert sync_calls[1] is second

    plugin.component.remove_choice('renamed')
    for data in tables:
        assert plugin._get_data_component_id(data, 'observed wavelength:renamed') is None
        assert 'observed wavelength:renamed' not in data.meta['_jdaviz_plugin_component_column']
    assert plugin.component_selected == 'default'
    plugin.component_redshift = 0.3
    for data in tables:
        assert_allclose(data['observed wavelength:default'], data['wavelength'] * 1.3)
    assert [cid.label for cid in auxiliary.main_components] == ['wavelength']
