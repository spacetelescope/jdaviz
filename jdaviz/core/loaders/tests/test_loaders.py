import numpy as np
import pytest
import time
from pathlib import Path
from itertools import product
from unittest.mock import patch

from astropy import units as u
from astropy.table import Table
from astropy.io import fits
from astropy.wcs import WCS
from astroquery.mast import Mast, MastMissions
from gwcs import WCS as GWCS
from specutils import SpectralRegion, Spectrum

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import find_matching_resolver
from jdaviz.utils import cached_uri


def test_loaders_registry(specviz_helper):
    # built-in loaders: file, url, etc
    assert len(specviz_helper.loaders) == len(loader_resolver_registry.members)


def test_open_close(specviz_helper):
    specviz_helper._app.state.dev_loaders = True

    assert specviz_helper._app.state.drawer_content == ''

    loader = specviz_helper.loaders['file']
    loader.open_in_tray()
    assert specviz_helper._app.state.drawer_content == 'loaders'
    loader.close_in_tray()
    assert specviz_helper._app.state.drawer_content == 'loaders'
    loader.close_in_tray(close_sidebar=True)
    assert specviz_helper._app.state.drawer_content == ''

    subset_plg = specviz_helper.plugins['Subset Tools']
    subset_plg.open_in_tray()
    assert specviz_helper._app.state.drawer_content == 'plugins'

    assert subset_plg._obj.loader_panel_ind is None  # loader panel not open
    subset_plg._obj.loaders['url'].open_in_tray()
    assert subset_plg._obj.loader_panel_ind == 0  # loader panel open
    subset_plg._obj.loaders['url'].close_in_tray()
    assert subset_plg._obj.loader_panel_ind is None  # loader panel not open
    subset_plg._obj.loaders['url'].close_in_tray(close_sidebar=True)
    assert specviz_helper._app.state.drawer_content == ''


def test_resolver_matching(specviz_helper):
    sp = Spectrum(spectral_axis=np.array([1, 2, 3])*u.nm,
                  flux=np.array([1, 2, 3])*u.Jy)

    res_sp = find_matching_resolver(specviz_helper._app, sp)
    assert res_sp._obj._registry_label == 'object'
    assert '1D Spectrum' in res_sp.format.choices

    specviz_helper.load(sp)
    assert len(specviz_helper._app.data_collection) == 1


def test_dbg_access(deconfigged_helper):
    test_data = np.array([1, 2, 3])
    deconfigged_helper.loaders['object'].object = test_data

    # test that _get_loader is successful to grab the object
    # and expose the underlying error
    with pytest.raises(ValueError, match="Cannot load as image with ndim=1"):  # noqa
        deconfigged_helper._get_loader('object', 'object', 'Image')


def test_trace_importer(specviz2d_helper, spectrum2d):
    specviz2d_helper._load(spectrum2d, format='2D Spectrum')

    trace = specviz2d_helper.plugins['2D Spectral Extraction'].export_trace()

    res_sp = find_matching_resolver(specviz2d_helper._app, trace)
    assert res_sp._obj._registry_label == 'object'
    assert res_sp.format == 'Trace'

    # import through loader API
    ldr = specviz2d_helper.loaders['object']
    ldr.object = trace
    assert ldr.format == 'Trace'
    ldr.importer.data_label = 'Trace 1'
    ldr.load()
    assert specviz2d_helper._app.data_collection[-1].label == 'Trace 1'

    # import through load method
    specviz2d_helper._load(trace, data_label='Trace 2')
    assert specviz2d_helper._app.data_collection[-1].label == 'Trace 2'


def test_spectrum2d_viewer_options(deconfigged_helper, spectrum2d):
    ldr = deconfigged_helper.loaders['object']
    ldr.object = spectrum2d
    ldr.format = '2D Spectrum'

    assert ldr.importer.viewer.create_new == '2D Spectrum'
    assert ldr.importer.viewer.new_label == '2D Spectrum'
    assert ldr.importer.ext_viewer.create_new == '1D Spectrum'
    assert ldr.importer.ext_viewer.new_label == '1D Spectrum'

    ldr.importer.ext_viewer.create_new = ''
    assert ldr.importer.ext_viewer == []

    assert ldr.importer.auto_extract
    ldr.load()

    # created 2D Spectrum viewer, did auto-extract,
    # but did not create 1D Spectrum viewer
    assert len(deconfigged_helper.viewers) == 1
    assert len(deconfigged_helper._app.data_collection) == 2


def test_markers_specviz2d_unit_conversion(specviz2d_helper, spectrum2d):
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    spectrum2d = Spectrum(flux=data*u.MJy, spectral_axis=data[3]*u.AA)
    specviz2d_helper.load_data(spectrum2d)


@pytest.mark.remote_data
@pytest.mark.filterwarnings(r"ignore::astropy.wcs.wcs.FITSFixedWarning")
@pytest.mark.xfail(reason='spectral_axis unit failure is due to a temporary fix'
                          ' used to avoid an error when handling 3D WCS with 2D data.'
                          'The temporary fix will be removed once an upstream solution'
                          'is implemented.')
def test_fits_spectrum2d(deconfigged_helper):
    uri = cached_uri('mast:jwst/product/jw02123-o001_v000000353_nirspec_f170lp-g235h_s2d.fits')
    if 'mast' in uri:
        ldr = deconfigged_helper.loaders['url']
        ldr.cache = True
        ldr.url = uri
    else:
        ldr = deconfigged_helper.loaders['file']
        ldr.filepath = uri

    assert '2D Spectrum' in ldr.format.choices
    ldr.format = '2D Spectrum'
    assert ldr.importer._obj._parser.__class__.__name__ == 'FITSParser'

    ldr.load()

    # ensure get_data works, retrieves a Spectrum1D object, and has spectral WCS attached correctly
    sp2d = deconfigged_helper.datasets['jw02123-o001_v000000353_nirspec_f170lp-g235h_s2d'].get_data()  # noqa
    assert isinstance(sp2d, Spectrum)
    assert str(sp2d.spectral_axis.unit) == 'um'

    sp1d = deconfigged_helper.datasets['jw02123-o001_v000000353_nirspec_f170lp-g235h_s2d (auto-ext)'].get_data()  # noqa
    assert isinstance(sp1d, Spectrum)
    assert str(sp1d.spectral_axis.unit) == 'um'


@pytest.mark.remote_data
@pytest.mark.filterwarnings(r"ignore::astropy.wcs.wcs.FITSFixedWarning")
@pytest.mark.filterwarnings(r"ignore::asdf.exceptions.AsdfPackageVersionWarning")
def test_jwst_wfss_bsub(deconfigged_helper):
    uri = 'https://stsci.box.com/shared/static/k5l446jid348jk343m8r4vvbkzk4syom.fits'
    ldr = deconfigged_helper.loaders['url']
    ldr.cache = True
    ldr.url = uri

    ldr.format = '2D Spectrum'  # may also be 'Image' depending on importer registry order

    ldr.load()

    sp1d = deconfigged_helper.datasets['k5l446jid348jk343m8r4vvbkzk4syom (auto-ext)'].get_data()  # noqa
    assert isinstance(sp1d, Spectrum)
    assert str(sp1d.spectral_axis.unit) == 'pix'


# TODO: Skip until file is uploaded to box
@pytest.mark.skip
def test_fits_spectrum_list_L3_wfss(deconfigged_helper):
    ldr = deconfigged_helper.loaders['url']
    # placeholder for WFSS L3 URI
    ldr.url = None

    # ldr = deconfigged_helper.loaders['file']
    # ldr.filepath = './jdaviz/notebooks/WFSS_fits/jw01076-o103_t0000_nircam_f356w-grismr_x1d.fits'  # noqa
    ldr.format = '1D Spectrum'

    # 1_117 is completely masked
    sources_obj = ldr.importer.sources
    number_combos = product((1, 2), (9, 17, 23))
    sources_obj.selected = [f'Exposure {e_num}, Source ID: {s_id}'
                            for e_num, s_id in number_combos]
    ldr.load()

    assert len(deconfigged_helper.datasets) == len(sources_obj.selected)
    dc = deconfigged_helper._app.data_collection
    assert len(dc) == len(sources_obj.selected)
    assert len(deconfigged_helper.viewers) == 1

    filestem = Path(ldr.filepath).stem
    for e_num, s_id in number_combos:
        spec = deconfigged_helper.datasets[f'{filestem}_EXP-{e_num}_ID-{s_id}'].get_data()
        assert isinstance(spec, Spectrum)
        assert str(spec.spectral_axis.unit) == 'um'


@pytest.mark.remote_data
def test_resolver_url(deconfigged_helper):

    loader = deconfigged_helper.loaders['url']

    # no url, no valid formats
    assert len(loader.format.choices) == 0

    # non-valid input
    with pytest.raises(ValueError, match="The input file 'not-valid-url' cannot be parsed as a "
                                         "URL or URI, and no existing local file is available at "
                                         "this path."):
        loader.url = 'not-valid-url'
    assert len(loader.format.choices) == 0

    # s3 input
    loader.url = "s3://stpubdata/jwst/public/jw02727/L3/t/o002/jw02727-o002_t062_nircam_clear-f277w_i2d.fits"  # noqa: E501
    assert loader._obj.url_scheme == 's3'
    assert len(loader.format.choices) > 0

    # https valid input (2D Spectrum)
    loader.url = 'https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits'  # noqa

    # may change with future importers
    assert len(loader.format.choices) == 3
    assert loader.format.selected == '2D Spectrum'  # default may change with future importers

    # test target filtering
    assert len(loader.target.choices) > 1
    assert loader.target.selected == 'Any'
    loader.target = '1D Spectrum'

    # may change with future importers
    assert len(loader.format.choices) == 1
    assert loader.format == '1D Spectrum'  # default may change with future importers
    assert loader.importer.data_label == 'exnkul627fcuhy5akf2gswytud5tazmw_index-0'  # noqa

    loader.target = 'Any'
    assert len(loader.format.choices) == 3
    loader.format = '2D Spectrum'
    assert loader.importer.data_label == 'exnkul627fcuhy5akf2gswytud5tazmw'  # noqa

    assert len(deconfigged_helper._app.data_collection) == 0
    assert len(deconfigged_helper.viewers) == 0

    loader.load()

    # 2D spectrum and auto-extracted 1D spectrum
    assert len(deconfigged_helper._app.data_collection) == 2
    assert len(deconfigged_helper.viewers) == 2

    with pytest.raises(ValueError, match="Failed query for URI"):
        # NOTE: this test will attempt to reach out to MAST via astroquery
        # even if cache is available.
        deconfigged_helper.load('mast:invalid')


def test_resolver_table_as_query(deconfigged_helper):
    ldr = deconfigged_helper.loaders['object']

    obs_table = Table({'id': [1, 2, 3], 'fileSetName': ['a', 'b', 'c']})
    file_table = Table({'id': [1, 2, 3], 'location': ['a', 'b', 'c']})
    invalid_table = Table({'id': [1, 2, 3], 'name': ['a', 'b', 'c']})

    assert ldr._obj.parsed_input_is_query is False

    ldr.object = obs_table
    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.observation_table_populated is True
    assert ldr._obj.file_table_populated is False

    ldr.object = file_table
    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.observation_table_populated is False
    assert ldr._obj.file_table_populated is True

    ldr.object = invalid_table
    assert ldr._obj.parsed_input_is_query is False


def test_hide_file_table_location_column(deconfigged_helper):
    """Test that hide_file_table_location_column setting works correctly."""
    # Test with setting disabled (default behavior)
    ldr = deconfigged_helper.loaders['object']
    file_table = Table({'id': [1, 2, 3],
                        'name': ['a', 'b', 'c'],
                        'location': ['http://a.fits', 'http://b.fits', 'http://c.fits']})

    ldr.object = file_table
    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.file_table_populated is True

    # location should be visible in both headers_avail and headers_visible
    assert 'location' in ldr._obj.file_table.headers_avail
    assert 'location' in ldr._obj.file_table.headers_visible

    # location data should exist in underlying table
    assert ldr._obj.file_table._qtable is not None
    assert 'location' in ldr._obj.file_table._qtable.colnames
    assert len(ldr._obj.file_table._qtable) == 3

    # Enable the setting and reload data
    deconfigged_helper._app.state.settings['hide_file_table_location_column'] = True

    # Clear the file table so file_table_populated will transition from False to True
    ldr._obj.file_table._clear_table()
    ldr._obj.file_table_populated = False

    # Now load new data to trigger the observer
    file_table2 = Table({'id': [4, 5],
                         'name': ['d', 'e'],
                         'location': ['http://d.fits', 'http://e.fits']})
    ldr.object = file_table2

    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.file_table_populated is True

    # location should NOT be in headers_avail (not in dropdown)
    assert 'location' not in ldr._obj.file_table.headers_avail
    # location should NOT be in headers_visible
    assert 'location' not in ldr._obj.file_table.headers_visible

    # But other columns should be visible
    assert 'id' in ldr._obj.file_table.headers_avail
    assert 'name' in ldr._obj.file_table.headers_avail

    # location data should still exist in underlying table for download functionality
    assert ldr._obj.file_table._qtable is not None
    assert 'location' in ldr._obj.file_table._qtable.colnames
    assert len(ldr._obj.file_table._qtable) == 2

    # Test changing setting back to False
    deconfigged_helper._app.state.settings['hide_file_table_location_column'] = False

    # Clear and reload to test re-enabling
    ldr._obj.file_table._clear_table()
    ldr._obj.file_table_populated = False

    file_table3 = Table({'id': [6], 'name': ['f'], 'location': ['http://f.fits']})
    ldr.object = file_table3

    # location should be visible again
    assert 'location' in ldr._obj.file_table.headers_avail
    assert 'location' in ldr._obj.file_table.headers_visible

    # Reset to default for other tests
    deconfigged_helper._app.state.settings['hide_file_table_location_column'] = False


def test_file_table_local_paths(deconfigged_helper):
    """Test that local file paths don't get MAST URL prefix."""
    ldr = deconfigged_helper.loaders['object']

    # Test various local path formats
    file_table = Table({
        'id': [1, 2, 3, 4, 5, 6, 7, 8],
        'location': [
            '/absolute/unix/path.fits',      # Unix absolute path
            './relative/path.fits',           # Unix relative path
            '../parent/path.fits',            # Unix parent relative path
            '~/home/path.fits',               # Home directory path
            'C:/windows/path.fits',           # Windows absolute path
            'C:\\windows\\backslash.fits',   # Windows absolute path with backslashes
            'http://example.com/file.fits',   # HTTP URL
            'jwst-product-name'               # MAST product name (no path indicators)
        ]
    })

    ldr.object = file_table
    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.file_table_populated is True

    # Test each path type
    test_cases = [
        (0, '/absolute/unix/path.fits', 'Unix absolute path'),
        (1, './relative/path.fits', 'Unix relative path'),
        (2, '../parent/path.fits', 'Unix parent relative path'),
        (3, '~/home/path.fits', 'Home directory path'),
        (4, 'C:/windows/path.fits', 'Windows absolute path with forward slashes'),
        (5, 'C:\\windows\\backslash.fits', 'Windows absolute path with backslashes'),
        (6, 'http://example.com/file.fits', 'HTTP URL'),
    ]

    for row_idx, expected_path, description in test_cases:
        ldr.file_table.select_rows(row_idx)
        result = ldr._obj.get_selected_url()
        assert result == expected_path, (
            f"Failed for {description}: expected {expected_path}, got {result}"
        )

    # Test MAST product name gets the prefix
    ldr.file_table.select_rows(7)
    result = ldr._obj.get_selected_url()
    assert result.startswith('https://mast.stsci.edu/search/jwst/api/'), \
        f"MAST product name should get URL prefix, got: {result}"
    assert 'jwst-product-name' in result, \
        f"MAST URL should contain the product name, got: {result}"


@pytest.mark.filterwarnings("ignore::UserWarning")
@pytest.mark.remote_data
def test_resolver_table_as_query_astroquery(deconfigged_helper, tmp_path):
    ldr = deconfigged_helper.loaders['object']

    mast = Mast()
    coords = mast.resolve_object("M101")

    jwst = MastMissions(mission='JWST')

    datasets = jwst.query_region(coords,
                                 radius=3,
                                 select_cols=["sci_stop_time", "sci_targname",
                                              "sci_start_time", "sci_status"],
                                 sort_by=['sci_targname'])

    ldr.object = datasets
    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.observation_table_populated is True
    assert ldr._obj.file_table_populated is False
    assert len(ldr.format.choices) == 0

    ldr.observation_table.select_rows(0)

    # file table is now populated asynchronously in a background thread;
    # poll briefly until it finishes
    deadline = time.time() + 30
    while not ldr._obj.file_table_populated and time.time() < deadline:
        time.sleep(0.1)

    assert ldr._obj.file_table_populated is True
    assert ldr._obj.get_selected_url() is None

    ldr.file_table.select_rows(0)
    assert ldr._obj.get_selected_url() is not None
    # we can't guarantee any specific format choices since
    # this depends on what data is returned from MAST
    # but let's at least make sure the download was successful
    # and points to a local temporary cache file
    assert len(ldr._obj.output) > 0


def test_invoke_from_plugin(specviz_helper, spectrum1d, tmp_path):
    s = SpectralRegion(5*u.um, 6*u.um)
    local_path = str(tmp_path / 'spectral_region.ecsv')
    s.write(local_path)

    specviz_helper.load_data(spectrum1d)

    loader = specviz_helper.plugins['Subset Tools'].loaders['file']

    assert len(loader.format.choices) == 0
    loader.filepath = local_path
    assert len(loader.format.choices) > 0

    loader.load()


# ── Server-side pagination / resolver threading tests ────────────────────────

def test_file_table_server_pagination_enabled(deconfigged_helper):
    """Resolver sets server_pagination=True on the file_table at init."""
    ldr = deconfigged_helper.loaders['object']
    assert ldr._obj.file_table.server_pagination is True


def test_fetch_and_populate_file_table_success(deconfigged_helper):
    """_fetch_and_populate_file_table populates file table via set_all_items_from_table."""
    ldr = deconfigged_helper.loaders['object']
    resolver = ldr._obj

    mock_file_table = Table({'name': ['file1.fits', 'file2.fits'],
                             'location': ['http://a.fits', 'http://b.fits']})

    with patch.object(resolver, '_get_product_list', return_value=mock_file_table), \
         patch.object(resolver, '_parsed_input_to_file_table', return_value=mock_file_table):
        resolver._fetch_and_populate_file_table(['dataset1'])

    assert resolver.file_table_populated is True
    assert resolver.file_table.server_items_length == 2
    assert len(resolver.file_table._all_items) == 2
    assert resolver.file_table.selected_rows == []


def test_fetch_and_populate_file_table_no_products(deconfigged_helper):
    """_fetch_and_populate_file_table handles no products by clearing the table."""
    ldr = deconfigged_helper.loaders['object']
    resolver = ldr._obj

    # Pre-populate so we can verify it gets cleared
    resolver.file_table._all_items = [{'name': 'old.fits'}]
    resolver.file_table.server_items_length = 1
    resolver.file_table_populated = True

    with patch.object(resolver, '_get_product_list', return_value=None), \
         patch.object(resolver, '_parsed_input_to_file_table', return_value=None):
        resolver._fetch_and_populate_file_table(['dataset1'])

    assert resolver.file_table_populated is False


def test_fetch_and_populate_file_table_resets_selection(deconfigged_helper):
    """_fetch_and_populate_file_table clears previous row selection before populating."""
    ldr = deconfigged_helper.loaders['object']
    resolver = ldr._obj

    # Simulate a pre-existing selection
    resolver.file_table.selected_rows = [{'name': 'old.fits', 'location': 'http://old.fits'}]

    mock_file_table = Table({'name': ['new.fits'], 'location': ['http://new.fits']})

    with patch.object(resolver, '_get_product_list', return_value=mock_file_table), \
         patch.object(resolver, '_parsed_input_to_file_table', return_value=mock_file_table):
        resolver._fetch_and_populate_file_table(['dataset1'])

    assert resolver.file_table.selected_rows == []


def test_on_observation_select_no_selection_clears_file_table(deconfigged_helper):
    """on_observation_select_changed clears file table when no observation is selected."""
    ldr = deconfigged_helper.loaders['object']
    resolver = ldr._obj

    # Pre-populate file table state
    resolver.file_table._all_items = [{'name': 'file.fits'}]
    resolver.file_table.server_items_length = 1
    resolver.file_table_populated = True

    # Ensure no rows are selected in the observation table
    resolver.observation_table.selected_rows = []
    resolver.on_observation_select_changed()

    assert resolver.file_table._all_items == []
    assert resolver.file_table.server_items_length == 0
    assert resolver.file_table_populated is False


@pytest.mark.parametrize('order', ([0, 1, 2], [0, 2, 1], [2, 0, 1], [2, 1, 0], [1, 2, 0]))
def test_mult_data_types(deconfigged_helper, image_nddata_wcs, spectrum2d, spectrum1d, order):
    datas = [image_nddata_wcs, spectrum2d, spectrum1d]
    load_kwargs = [{'format': 'Image'},
                   {'format': '2D Spectrum', 'auto_extract': True},
                   {'format': '1D Spectrum'}]

    for i in order:
        deconfigged_helper.load(datas[i], **load_kwargs[i])

    # NOTE: 2D Spectrum will also result in auto-extracted 1D Spectrum
    assert len(deconfigged_helper._app.data_collection) == 4
    assert len(deconfigged_helper.viewers) == 3


def test_freq_wavelength_linking(deconfigged_helper, spectrum1d):
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='sp_wavelength')
    sp1d_freq = Spectrum(spectral_axis=spectrum1d.spectral_axis.to(u.Hz, equivalencies=u.spectral()),  # noqa
                         flux=spectrum1d.flux,
                         uncertainty=spectrum1d.uncertainty,
                         mask=spectrum1d.mask,
                         meta=spectrum1d.meta)
    deconfigged_helper.load(sp1d_freq, format='1D Spectrum', data_label='sp_frequency')

    # flux <> flux, uncertainty <> uncertainty, wavelength <> freq, Pixel 0[x] <> Pixel 1[x]
    assert len(deconfigged_helper._app.data_collection.external_links) == 4


def test_load_image_mult_sci_extension(imviz_helper):
    # test loading an image with multiple SCI extensions and
    # ensure that automatic parenting logic is handled correctly
    arr = np.zeros((2, 2), dtype=np.float32)
    hdul = fits.HDUList([fits.PrimaryHDU(),
                        fits.ImageHDU(arr, name='SCI', ver=1),
                        fits.ImageHDU(arr, name='ERR', ver=1),
                        fits.ImageHDU(arr, name='SCI', ver=2),
                        fits.ImageHDU(arr, name='ERR', ver=2)
                         ])

    # imviz_helper._load(hdul, extension=('SCI,1', 'SCI,2', 'ERR,2'))
    imviz_helper.load_data(hdul, ext=('SCI,1', 'SCI,2', 'ERR,2'))

    assert len(imviz_helper._app.data_collection) == 3
    assert [d.label for d in imviz_helper._app.data_collection] == ['Image[SCI,1]', 'Image[SCI,2]', 'Image[ERR,2]']  # noqa

    assert imviz_helper._app._get_assoc_data_children('Image[SCI,1]') == []
    assert imviz_helper._app._get_assoc_data_children('Image[SCI,2]') == ['Image[ERR,2]']
    assert imviz_helper._app._get_assoc_data_parent('Image[ERR,2]') == 'Image[SCI,2]'


def test_loaders_extension_select(imviz_helper):
    # tests internal logic of SelectFileExtensionComponent
    arr = np.zeros((2, 2), dtype=np.float32)
    hdul = fits.HDUList([fits.PrimaryHDU(),
                        fits.ImageHDU(arr, name='SCI', ver=1),
                        fits.ImageHDU(arr, name='ERR', ver=1),
                        fits.ImageHDU(arr, name='SCI', ver=2),
                        fits.ImageHDU(arr, name='ERR', ver=2)
                         ])

    ldr = imviz_helper.loaders['object']
    ldr.object = hdul

    # test setting extension by index: [name, ver], [name,ver], and name,ver
    ldr.importer.extension = ['1: [SCI,1]', '[SCI,2]', 'ERR,2']
    assert ldr.importer.extension.selected == ['1: [SCI,1]',
                                               '3: [SCI,2]',
                                               '4: [ERR,2]']
    assert ldr.importer.extension.selected_index == [1, 3, 4]

    # if not providing ver, first match will be used
    ldr.importer.extension = 'SCI'
    assert ldr.importer.extension.selected == ['1: [SCI,1]']

    # case of providing index
    ldr.importer.extension = [1, 3]
    assert ldr.importer.extension.selected == ['1: [SCI,1]', '3: [SCI,2]']


def test_load_image_align_by(deconfigged_helper, image_nddata_wcs):
    ldr = deconfigged_helper.loaders['object']
    ldr.object = image_nddata_wcs
    assert 'Image' in ldr.format.choices
    ldr.format = 'Image'

    assert ldr.importer.align_by == 'Pixels'

    ldr.load()

    assert deconfigged_helper.plugins['Orientation'].align_by.selected == 'Pixels'

    ldr.importer.align_by = 'WCS'
    ldr.load()

    assert deconfigged_helper.plugins['Orientation'].align_by.selected == 'WCS'


@pytest.mark.remote_data
@pytest.mark.parametrize(
    ('gwcs_to_fits_sip', 'expected_cls'),
    ((True, WCS), (False, GWCS),), ids=('True-WCS', 'False-GWCS'))
@pytest.mark.filterwarnings("ignore:Some non-standard WCS keywords were excluded")
def test_gwcs_to_fits_sip(gwcs_to_fits_sip, expected_cls, deconfigged_helper):
    """Test gwcs_to_fits_sip through the importer API."""
    ldr = deconfigged_helper.loaders['url']
    ldr.url = 'https://data.science.stsci.edu/redirect/JWST/jwst-data_analysis_tools/imviz_test_data/jw00042001001_01101_00001_nrcb5_cal.fits'  # noqa
    ldr.importer.gwcs_to_fits_sip = gwcs_to_fits_sip

    ldr.load()

    data = deconfigged_helper._app.data_collection[0]
    assert isinstance(data.coords, expected_cls)


@pytest.mark.remote_data
class TestRomanLoaders:
    # Use dictionary to make it easier to parametrize tests
    # and extend in the future via parametrization of test_rdd_open
    roman_uris = {
        '1D Spectrum': 'https://stsci.box.com/shared/static/rgasl942so9hno2rq9f1xgdeolav59o5.asdf',
        '2D Spectrum': 'https://stsci.box.com/shared/static/g8yb9hxguy3aedveef9su67lesgd8c6w.asdf'
    }

    # roman_datamodels isn't a required dependency and some workflows don't install it
    try:
        from roman_datamodels import datamodels as rdd
    except ImportError:
        rdd = None

    @pytest.mark.skip
    @pytest.mark.parametrize('data_type', roman_uris.keys())
    def test_rdd_open(self, data_type):
        if self.rdd is not None:
            # Ensure that roman_datamodels can open the test files
            self.rdd.open(self.roman_uris[data_type])
        else:
            # Skip the test if roman_datamodels is not installed
            pytest.skip("roman_datamodels not installed")

    @pytest.mark.parametrize('helper', ['deconfigged_helper', 'specviz_helper'])
    def test_roman_1d_spectrum(self, helper, request):
        helper = request.getfixturevalue(helper)
        ldr = helper.loaders['url']
        # wfi_spec_combined_1d_r0000201001001001001_0002_WFI01.asdf
        ldr.url = self.roman_uris['1D Spectrum']
        ldr.format = '1D Spectrum'
        assert len(ldr.importer.extension.choices) > 1

        ldr.load()
        assert len(helper._app.data_collection) == 1

    @pytest.mark.parametrize('helper', ['deconfigged_helper', 'specviz2d_helper'])
    def test_roman_2d_spectrum(self, helper, request):
        helper = request.getfixturevalue(helper)
        ldr = helper.loaders['url']
        # wfi_spec_decontaminated_2d_r0000201001001001001_0002_WFI01.asdf
        ldr.url = self.roman_uris['2D Spectrum']
        ldr.format = '2D Spectrum'
        assert len(ldr.importer.extension.choices) > 1

        ldr.load()
        # 2D spectrum and auto-extracted 1D spectrum
        assert len(helper._app.data_collection) == 2


@pytest.fixture
def table_spectrum_hdulist_single_row():
    """
    Create a minimal Binary Table HDU with spectral data in array-valued columns.
    This mimics the structure of VO-compliant spectra like BEFS and FUSE.
    Single row with array values (shape: 1 x N_wavelengths).
    """
    # Create wavelength and flux arrays
    n_points = 100
    wave = np.linspace(1000, 2000, n_points)
    flux = np.random.random(n_points) * 1e-13
    sigma = np.random.random(n_points) * 1e-14

    # Create a Binary Table HDU with array-valued columns
    # Format: '100E' means 100 float32 values
    col_wave = fits.Column(name='WAVE', format=f'{n_points}E', unit='Angstrom', array=[wave])
    col_flux = fits.Column(name='FLUX', format=f'{n_points}E',
                           unit='erg/s/cm2/Angstrom', array=[flux])
    col_sigma = fits.Column(name='SIGMA', format=f'{n_points}E',
                            unit='erg/s/cm2/Angstrom', array=[sigma])

    hdu = fits.BinTableHDU.from_columns([col_wave, col_flux, col_sigma])
    hdu.name = 'SPECTRUM'

    primary = fits.PrimaryHDU()
    return fits.HDUList([primary, hdu])


@pytest.fixture
def table_spectrum_hdulist_with_flux_reduced():
    """
    Create a Binary Table HDU with FLUX_REDUCED and ERR_REDUCED columns.
    This mimics the structure of ESO archive spectra.
    Single row with array values.
    """
    n_points = 150
    wave = np.linspace(500, 1500, n_points)
    flux = np.random.random(n_points) * 1e-12
    err = np.random.random(n_points) * 1e-13
    snr = flux / err

    col_wave = fits.Column(name='WAVE', format=f'{n_points}D', unit='nm', array=[wave])
    col_flux = fits.Column(name='FLUX_REDUCED', format=f'{n_points}D',
                           unit='erg/s/cm2/nm', array=[flux])
    col_err = fits.Column(name='ERR_REDUCED', format=f'{n_points}D',
                          unit='erg/s/cm2/nm', array=[err])
    col_snr = fits.Column(name='SNR', format=f'{n_points}D', array=[snr])

    hdu = fits.BinTableHDU.from_columns([col_wave, col_flux, col_err, col_snr])
    hdu.name = 'SPECTRUM'

    primary = fits.PrimaryHDU()
    return fits.HDUList([primary, hdu])


def test_table_spectrum_single_row(deconfigged_helper, table_spectrum_hdulist_single_row):
    """Test loading Binary Table HDU with single row array-valued columns (WAVE, FLUX, SIGMA)."""
    ldr = deconfigged_helper.loaders['object']
    ldr.object = table_spectrum_hdulist_single_row

    # Should detect as 1D Spectrum
    assert '1D Spectrum' in ldr.format.choices
    ldr.format = '1D Spectrum'

    # Should have flux extension available
    assert len(ldr.importer.extension.choices) > 0

    # Load the data
    ldr.load()

    # Verify spectrum was loaded
    assert len(deconfigged_helper._app.data_collection) == 1
    spec = deconfigged_helper.datasets['1D Spectrum'].get_data()

    # Verify it's a proper Spectrum object
    assert isinstance(spec, Spectrum)
    assert spec.flux.shape == (100,)
    assert spec.spectral_axis.shape == (100,)

    # Verify units were preserved
    assert str(spec.spectral_axis.unit) == 'Angstrom'
    # Unit ordering may vary, so check components
    flux_unit_str = str(spec.flux.unit)
    assert 'erg' in flux_unit_str
    assert 'Angstrom' in flux_unit_str
    assert 'cm2' in flux_unit_str or 'cm**2' in flux_unit_str
    assert 's' in flux_unit_str

    # Verify uncertainty was loaded
    assert spec.uncertainty is not None
    assert spec.uncertainty.array.shape == (100,)


def test_table_spectrum_flux_reduced(deconfigged_helper, table_spectrum_hdulist_with_flux_reduced):
    """Test loading Binary Table HDU with FLUX_REDUCED and ERR_REDUCED columns."""
    ldr = deconfigged_helper.loaders['object']
    ldr.object = table_spectrum_hdulist_with_flux_reduced

    # Should detect as 1D Spectrum
    assert '1D Spectrum' in ldr.format.choices
    ldr.format = '1D Spectrum'

    # Load the data
    ldr.load()

    # Verify spectrum was loaded
    assert len(deconfigged_helper._app.data_collection) == 1
    spec = deconfigged_helper.datasets['1D Spectrum'].get_data()

    # Verify it's a proper Spectrum object
    assert isinstance(spec, Spectrum)
    assert spec.flux.shape == (150,)
    assert spec.spectral_axis.shape == (150,)

    # Verify units were preserved
    assert str(spec.spectral_axis.unit) == 'nm'
    # Unit ordering may vary, so check components
    flux_unit_str = str(spec.flux.unit)
    assert 'erg' in flux_unit_str
    assert 'nm' in flux_unit_str
    assert 'cm2' in flux_unit_str or 'cm**2' in flux_unit_str
    assert 's' in flux_unit_str

    # Verify uncertainty was loaded from ERR_REDUCED column
    assert spec.uncertainty is not None
    assert spec.uncertainty.array.shape == (150,)


@pytest.fixture
def table_spectrum_no_flux_column():
    """
    Create a Binary Table HDU with WAVE column but NO recognized flux column.
    This tests the case where a binary HDU doesn't match prescribed flux column names.
    """
    n_points = 100
    wave = np.linspace(1000, 2000, n_points)
    data = np.random.random(n_points) * 1e-13  # Some data with non-flux column name

    col_wave = fits.Column(name='WAVE', format=f'{n_points}E', unit='Angstrom', array=[wave])
    # Use a column name that does NOT match any flux pattern
    col_data = fits.Column(name='INTENSITY', format=f'{n_points}E',
                           unit='counts', array=[data])

    hdu = fits.BinTableHDU.from_columns([col_wave, col_data])
    hdu.name = 'SPECTRUM'

    primary = fits.PrimaryHDU()
    return fits.HDUList([primary, hdu])


def test_table_spectrum_no_flux_column(deconfigged_helper, table_spectrum_no_flux_column):
    """Test that Binary Table HDU without recognized flux column names is not loaded as spectrum."""
    ldr = deconfigged_helper.loaders['object']
    ldr.object = table_spectrum_no_flux_column

    # Should NOT detect as 1D Spectrum since there's no recognized flux column
    assert '1D Spectrum' not in ldr.format.choices


def test_invalid_kwargs_error_message(specviz_helper, spectrum1d):
    """Test that invalid kwargs to .load() produce a helpful error message with format name."""
    # Load should fail when passing multiple invalid kwargs
    # and the error message should include the format name
    with pytest.raises(ValueError, match=r"Invalid argument for 1D Spectrum format: "
                                         r"invalid_arg1, invalid_arg2"):
        specviz_helper.load(spectrum1d, format='1D Spectrum',
                            invalid_arg1='foo', invalid_arg2='bar')


def test_load_cube_no_dq_in_viewer(deconfigged_helper):
    """
    Test loading a cube that has a DQ extension but using setting the
    'Add to Flux Viewer' toggle to False so the DQ cube is only added to the
    data collection.
    """

    flux_data = np.ones((5, 10, 10), dtype=np.float32)
    dq_data = np.zeros((5, 10, 10), dtype=np.int32)

    # create HDUList with Primary + FLUX + DQ extensions
    hdul = fits.HDUList([
        fits.PrimaryHDU(),
        fits.ImageHDU(data=flux_data, name='FLUX'),
        fits.ImageHDU(data=dq_data, name='DQ')
    ])

    deconfigged_helper.load(hdul, format='3D Spectrum', dq_add_to_flux_viewer=False)

    # make sure the flux viewer '3D Spectrum' only has one dataset loaded
    data_in_flux_viewer = deconfigged_helper.viewers['3D Spectrum'].data_menu.data_labels_loaded
    assert len(data_in_flux_viewer) == 1
    assert '3D Spectrum' in data_in_flux_viewer

    # but the DQ extension should be in the data collection, along with FLUX and
    # the automatic extraction for a total of 3 items
    datasets = deconfigged_helper.datasets
    assert len(datasets) == 3
    assert '3D Spectrum [DQ]' in datasets
