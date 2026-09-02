import astropy.units as u
import numpy as np
from astropy.table import QTable
from numpy.testing import assert_allclose


def test_spectral_lines_relevancy(deconfigged_helper, spectrum1d, image_nddata_wcs):
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


def test_spectral_lines_components(deconfigged_helper, spectrum1d):
    # load a spectrum1d that spans 6000-8000 angstrom
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='my_spec')

    # 'plugins' dict only exposes relevant plugins, so fetch from tray directly
    plugin = deconfigged_helper._app.get_tray_item_from_name('g-spectral-lines')

    # import a line list with lines in range of the loaded spectrum
    rest_wav = np.array([6562.8, 7000.0])
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'wavelength': rest_wav * u.AA, 'name': ['Ha', 'line2']})
    ldr.format = 'Spectral Lines'
    ldr.importer()

    # plugin picked up the table and added a column for the default component
    assert plugin.line_table != ''
    line_data = deconfigged_helper._app.data_collection[plugin.line_table]

    def col(component_lbl):
        cid = plugin._get_data_component_id(line_data,
                                            f'rest wavelength:{component_lbl}')
        assert cid is not None
        return line_data[cid]

    assert plugin.component_selected == 'default'
    assert_allclose(col('default'), rest_wav)

    # a new component gets its own column, initially unshifted (z=0)
    plugin.component.add_choice('second')
    assert plugin.component_selected == 'second'
    assert plugin.component_redshift == 0
    assert_allclose(col('second'), rest_wav)

    # adjusting the redshift updates only the selected component's column
    plugin.component_redshift = 0.1
    assert_allclose(col('second'), rest_wav * 1.1)
    assert_allclose(col('default'), rest_wav)

    # renaming moves the shifted column to the new name and keeps the redshift
    plugin.component.rename_choice('second', 'renamed')
    assert plugin._get_data_component_id(line_data, 'rest wavelength:second') is None
    assert_allclose(col('renamed'), rest_wav * 1.1)
    assert plugin.component_selected == 'renamed'
    assert plugin.component_redshift == 0.1

    # removing a component removes its column, leaving others untouched
    plugin.component.remove_choice('renamed')
    assert plugin._get_data_component_id(line_data, 'rest wavelength:renamed') is None
    assert plugin.component_selected == 'default'
    assert plugin.component_redshift == 0
    assert_allclose(col('default'), rest_wav)
