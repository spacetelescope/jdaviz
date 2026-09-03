import astropy.units as u
import numpy as np
from astropy.table import QTable
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
    importer.viewer.create_new = 'Table'
    importer()

    # a table viewer showing spectral-line data should make the plugin relevant
    # even without a spectrum viewer
    assert plugin.irrelevant_msg == ''

    # removing the table viewer's data should make it irrelevant again
    deconfigged_helper._app.data_item_remove(deconfigged_helper._app.data_collection[0].label)
    assert plugin.irrelevant_msg != ''


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

    # component_lines reflects the fallback to 'default', unshifted and visible
    assert_allclose(component_lines_field('obs'), rest_wav)
    assert component_lines_field('show') == [True, True]
