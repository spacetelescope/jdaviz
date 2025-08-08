import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from gwcs import WCS as GWCS
from specutils import SpectralRegion, Spectrum
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import find_matching_resolver
from jdaviz.utils import cached_uri


def test_loaders_registry(specviz_helper):
    # built-in loaders: file, url, etc
    assert len(specviz_helper.loaders) == len(loader_resolver_registry.members)


def test_open_close(specviz_helper):
    specviz_helper.app.state.dev_loaders = True

    assert specviz_helper.app.state.drawer_content == ''

    loader = specviz_helper.loaders['file']
    loader.open_in_tray()
    assert specviz_helper.app.state.drawer_content == 'loaders'
    loader.close_in_tray()
    assert specviz_helper.app.state.drawer_content == 'loaders'
    loader.close_in_tray(close_sidebar=True)
    assert specviz_helper.app.state.drawer_content == ''

    subset_plg = specviz_helper.plugins['Subset Tools']
    subset_plg.open_in_tray()
    assert specviz_helper.app.state.drawer_content == 'plugins'

    assert subset_plg._obj.loader_panel_ind is None  # loader panel not open
    subset_plg._obj.loaders['url'].open_in_tray()
    assert subset_plg._obj.loader_panel_ind == 0  # loader panel open
    subset_plg._obj.loaders['url'].close_in_tray()
    assert subset_plg._obj.loader_panel_ind is None  # loader panel not open
    subset_plg._obj.loaders['url'].close_in_tray(close_sidebar=True)
    assert specviz_helper.app.state.drawer_content == ''


def test_resolver_matching(specviz_helper):
    sp = Spectrum(spectral_axis=np.array([1, 2, 3])*u.nm,
                  flux=np.array([1, 2, 3])*u.Jy)

    res_sp = find_matching_resolver(specviz_helper.app, sp)
    assert res_sp._obj._registry_label == 'object'
    assert res_sp.format == '1D Spectrum'

    specviz_helper._load(sp)
    assert len(specviz_helper.app.data_collection) == 1


def test_trace_importer(specviz2d_helper, spectrum2d):
    specviz2d_helper._load(spectrum2d, format='2D Spectrum')

    trace = specviz2d_helper.plugins['2D Spectral Extraction'].export_trace()

    res_sp = find_matching_resolver(specviz2d_helper.app, trace)
    assert res_sp._obj._registry_label == 'object'
    assert res_sp.format == 'Trace'

    # import through loader API
    ldr = specviz2d_helper.loaders['object']
    ldr.object = trace
    assert ldr.format == 'Trace'
    ldr.importer.data_label = 'Trace 1'
    ldr.importer()
    assert specviz2d_helper.app.data_collection[-1].label == 'Trace 1'

    # import through load method
    specviz2d_helper._load(trace, data_label='Trace 2')
    assert specviz2d_helper.app.data_collection[-1].label == 'Trace 2'


def test_markers_specviz2d_unit_conversion(specviz2d_helper, spectrum2d):
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    spectrum2d = Spectrum(flux=data*u.MJy, spectral_axis=data[3]*u.AA)
    specviz2d_helper.load_data(spectrum2d)


@pytest.mark.remote_data
@pytest.mark.filterwarnings(r"ignore::astropy.wcs.wcs.FITSFixedWarning")
def test_fits_spectrum2d(deconfigged_helper):
    uri = cached_uri('mast:jwst/product/jw02123-o001_v000000353_nirspec_f170lp-g235h_s2d.fits')
    if 'mast' in uri:
        ldr = deconfigged_helper.loaders['url']
        ldr.cache = True
        ldr.url = uri
    else:
        ldr = deconfigged_helper.loaders['file']
        ldr.filepath = uri

    # Default is Image but the test switches to 2D Spectrum
    # since this file type is not yet supported by the image loader
    assert ldr.format == 'Image'
    assert ldr.importer._obj.input_has_extensions is True

    ldr.format = '2D Spectrum'

    ldr.importer()

    # ensure get_data works, retrieves a Spectrum1D object, and has spectral WCS attached correctly
    sp2d = deconfigged_helper.get_data('jw02123-o001_v000000353_nirspec_f170lp-g235h_s2d')  # noqa
    assert isinstance(sp2d, Spectrum)
    assert str(sp2d.spectral_axis.unit) == 'um'

    sp1d = deconfigged_helper.get_data('jw02123-o001_v000000353_nirspec_f170lp-g235h_s2d (auto-ext)')  # noqa
    assert isinstance(sp1d, Spectrum)
    assert str(sp1d.spectral_axis.unit) == 'um'


@pytest.mark.remote_data
def test_resolver_url(deconfigged_helper):
    loader = deconfigged_helper.loaders['url']

    # no url, no valid formats
    assert len(loader.format.choices) == 0

    # non-valid input
    loader.url = 'not-valid-url'
    assert len(loader.format.choices) == 0

    # s3 input
    loader.url = "s3://stpubdata/jwst/public/jw02727/L3/t/o002/jw02727-o002_t062_nircam_clear-f277w_i2d.fits"  # noqa: E501
    assert loader._obj.url_scheme == 's3'
    assert len(loader.format.choices) > 0

    # https valid input
    loader.url = 'https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits'  # noqa
    assert len(loader.format.choices) == 4  # may change with future importers
    assert loader.format.selected == 'Image'  # default may change with future importers

    # test target filtering
    assert len(loader.target.choices) > 1
    assert loader.target.selected == 'Any'
    loader.target = '1D Spectrum'
    assert len(loader.format.choices) == 2  # may change with future importers
    assert loader.format == '1D Spectrum List'  # default may change with future importers
    assert loader.importer.data_label == 'exnkul627fcuhy5akf2gswytud5tazmw'  # noqa

    loader.target = 'Any'
    assert len(loader.format.choices) == 4
    loader.format = '2D Spectrum'
    assert loader.importer.data_label == 'exnkul627fcuhy5akf2gswytud5tazmw'  # noqa

    assert len(deconfigged_helper.app.data_collection) == 0
    assert len(deconfigged_helper.viewers) == 0

    loader.importer()

    # 2D spectrum and auto-extracted 1D spectrum
    assert len(deconfigged_helper.app.data_collection) == 2
    assert len(deconfigged_helper.viewers) == 2

    with pytest.raises(ValueError, match="Failed query for URI"):
        # NOTE: this test will attempt to reach out to MAST via astroquery
        # even if cache is available.
        deconfigged_helper.load('mast:invalid')


def test_invoke_from_plugin(specviz_helper, spectrum1d, tmp_path):
    s = SpectralRegion(5*u.um, 6*u.um)
    local_path = str(tmp_path / 'spectral_region.ecsv')
    s.write(local_path)

    specviz_helper.load_data(spectrum1d)

    loader = specviz_helper.plugins['Subset Tools'].loaders['file']

    assert len(loader.format.choices) == 0
    loader.filepath = local_path
    assert len(loader.format.choices) > 0

    loader.importer()


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

    assert len(imviz_helper.app.data_collection) == 3
    assert [d.label for d in imviz_helper.app.data_collection] == ['Image[SCI,1]', 'Image[SCI,2]', 'Image[ERR,2]']  # noqa

    assert imviz_helper.app._get_assoc_data_children('Image[SCI,1]') == []
    assert imviz_helper.app._get_assoc_data_children('Image[SCI,2]') == ['Image[ERR,2]']
    assert imviz_helper.app._get_assoc_data_parent('Image[ERR,2]') == 'Image[SCI,2]'


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

    ldr.importer()

    data = deconfigged_helper.app.data_collection[0]
    assert isinstance(data.coords, expected_cls)
