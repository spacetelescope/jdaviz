import pytest
import stdatamodels
from astropy import units as u
from astropy.utils.data import download_file
from glue.core.edit_subset_mode import NewMode
from glue.core.roi import XRangeROI
from specutils import Spectrum

from jdaviz.utils import PRIHDR_KEY, cached_uri
from jdaviz.configs.imviz.tests.utils import create_example_gwcs


@pytest.mark.remote_data
def test_2d_parser_jwst(specviz2d_helper):
    fn = download_file('https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits', cache=True)  # noqa

    specviz2d_helper.load_data(spectrum_2d=fn)
    assert len(specviz2d_helper.app.data_collection) == 2

    dc_0 = specviz2d_helper.app.data_collection[0]
    assert dc_0.label == 'Spectrum 2D'
    assert PRIHDR_KEY not in dc_0.meta
    assert 'header' not in dc_0.meta
    assert dc_0.meta['DETECTOR'] == 'MIRIMAGE'
    assert dc_0.get_component('flux').units == 'MJy / sr'

    dc_1 = specviz2d_helper.app.data_collection[1]
    assert dc_1.label == 'Spectrum 1D'
    assert 'header' not in dc_1.meta

    # extracted 1D spectrum should have same flux units as 2d spectrum
    assert dc_1.get_component('flux').units == dc_0.get_component('flux').units

    # Also check the coordinates info panel.
    viewer_2d = specviz2d_helper.app.get_viewer('spectrum-2d-viewer')
    label_mouseover = specviz2d_helper._coords_info
    label_mouseover._viewer_mouse_event(viewer_2d,
                                        {'event': 'mousemove', 'domain': {'x': 350, 'y': 30}})
    assert label_mouseover.as_text() == ('Pixel x=0350.0 y=0030.0 Value +3.22142e+04 MJy / sr',
                                         'Wave 6.24985e+00 um', '')


@pytest.mark.remote_data
@pytest.mark.filterwarnings(r"ignore::astropy.wcs.wcs.FITSFixedWarning")
def test_2d_parser_ext_hdulist(specviz2d_helper):
    # jw01538-o160_s00004_nirspec_f170lp-g235h-s1600a1-sub2048_s2d
    specviz2d_helper.load('https://stsci.box.com/shared/static/l1dmioxuvtzyuq1p7o9wvjq8pph2yqkk.fits', cache=True)  # noqa
    dc_0 = specviz2d_helper.app.data_collection[0]
    assert dc_0.get_component('flux').shape == (29, 3416)


@pytest.mark.remote_data
def test_hlsp_goods_s2d(specviz2d_helper):
    uri='mast:HLSP/jades/dr3/goods-n/spectra/clear-prism/goods-n-mediumhst/hlsp_jades_jwst_nirspec_goods-n-mediumhst-00000804_clear-prism_v1.0_s2d.fits'  # noqa
    specviz2d_helper.load(cached_uri(uri),
                          cache=True)

    # ensure uncalibrated 2d spectrum extraction works
    assert len(specviz2d_helper.app.data_collection) == 2

    dc_0 = specviz2d_helper.app.data_collection[0]
    assert dc_0.get_component('flux').shape == (27, 674)


@pytest.mark.remote_data
def test_hlsp_goods_s2d_deconfigged(deconfigged_helper):
    uri = 'mast:HLSP/jades/dr3/goods-n/spectra/clear-prism/goods-n-mediumhst/hlsp_jades_jwst_nirspec_goods-n-mediumhst-00000804_clear-prism_v1.0_s2d.fits'  # noqa
    deconfigged_helper.load(cached_uri(uri),
                            format='2D Spectrum',
                            data_label='2D Spectrum',
                            cache=True)

    # ensure uncalibrated 2d spectrum extraction works
    assert len(deconfigged_helper.app.data_collection) == 2

    dc_0 = deconfigged_helper.app.data_collection[0]
    assert dc_0.get_component('flux').shape == (27, 674)
    assert isinstance(deconfigged_helper.plugins['2D Spectral Extraction'].trace_dataset.selected_obj, Spectrum)  # noqa
    # TODO: store expected class in data itself so get_data doesn't need to pass cls
    assert isinstance(deconfigged_helper.get_data('2D Spectrum', cls=Spectrum), Spectrum)


def test_2d_parser_no_unit(specviz2d_helper, mos_spectrum2d):
    specviz2d_helper.load_data(mos_spectrum2d, spectrum_2d_label='my_2d_spec')
    assert len(specviz2d_helper.app.data_collection) == 2

    dc_0 = specviz2d_helper.app.data_collection[0]
    assert dc_0.label == 'my_2d_spec 2D'
    assert dc_0.get_component('flux').units == 'Jy'

    dc_1 = specviz2d_helper.app.data_collection[1]
    assert dc_1.label == 'my_2d_spec 1D'
    assert dc_1.get_component('flux').units == dc_0.get_component('flux').units

    # Also check the coordinates info panels.

    viewer_2d = specviz2d_helper.app.get_viewer('spectrum-2d-viewer')
    label_mouseover = specviz2d_helper._coords_info
    label_mouseover._viewer_mouse_event(viewer_2d,
                                        {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ('Pixel x=00000.0 y=00000.0 Value +3.74540e-01 Jy',
                                         'Wave 1.00000e-06 m', '')
    assert label_mouseover.icon == 'a'

    viewer_1d = specviz2d_helper.app.get_viewer('spectrum-viewer')
    # need to trigger a mouseleave or mouseover to reset the traitlets
    label_mouseover._viewer_mouse_event(viewer_1d, {'event': 'mouseenter'})
    label_mouseover._viewer_mouse_event(viewer_1d,
                                        {'event': 'mousemove', 'domain': {'x': 7.2e-6, 'y': 3}})
    assert label_mouseover.as_text() == ('Cursor 7.20000e-06, 3.00000e+00',
                                         'Wave 7.00000e-06 m (6 pix)',
                                         'Flux 6.92896e-02 Jy')

    assert label_mouseover.icon == 'b'


def test_2d_parser_hdulist_ext(tmp_path, specviz2d_helper, mos_spectrum2d_as_hdulist):
    in_filename = tmp_path / "my_2d_spec.fits"

    # Create a dummy ASDF extension to trick specutil to use JWST s2d parser.
    # The actual values do not matter here; they are currently nonsense.
    w = create_example_gwcs(mos_spectrum2d_as_hdulist['SCI'].data.shape)
    w.bounding_box = ((-1, 2.9), (6, 7.5))
    tree = {
        'model': {
            'sci': {
                'data': mos_spectrum2d_as_hdulist['SCI'].data
            }
        },
        'meta': {'wcs': w}
    }
    stdatamodels.asdf_in_fits.write(in_filename, tree, mos_spectrum2d_as_hdulist, overwrite=True)

    specviz2d_helper.load_data(in_filename, ext=1)
    assert len(specviz2d_helper.app.data_collection) == 2

    dc_0 = specviz2d_helper.app.data_collection[0]
    assert dc_0.label == 'Spectrum 2D'
    assert dc_0.get_component('flux').units == 'ct'

    dc_1 = specviz2d_helper.app.data_collection[1]
    assert dc_1.label == 'Spectrum 1D'
    assert dc_1.get_component('flux').units == dc_0.get_component('flux').units

    # The rest already checked in test_2d_parser_no_unit above.


def test_1d_parser(specviz2d_helper, spectrum1d):
    specviz2d_helper.load_data(spectrum_1d=spectrum1d)
    assert len(specviz2d_helper.app.data_collection) == 1
    dc_0 = specviz2d_helper.app.data_collection[0]
    assert dc_0.label == 'Spectrum 1D'
    assert dc_0.meta['uncertainty_type'] == 'std'


def test_2d_1d_parser(specviz2d_helper, mos_spectrum2d, spectrum1d):
    specviz2d_helper.load_data(spectrum_2d=mos_spectrum2d, spectrum_1d=spectrum1d)
    assert specviz2d_helper.app.data_collection.labels == ['Spectrum 2D', 'Spectrum 1D']

    spec2d_viewer = specviz2d_helper.app.get_viewer('spectrum-2d-viewer')
    assert spec2d_viewer.figure.axes[0].label == "x: pixels"  # -0.5, 14.5
    spec2d_viewer.apply_roi(XRangeROI(10, 12))

    spec2d_viewer.session.edit_subset_mode._mode = NewMode

    spec1d_viewer = specviz2d_helper.app.get_viewer('spectrum-viewer')
    assert spec1d_viewer.figure.axes[0].label == "Wavelength [Angstrom]"  # 6000, 8000
    spec1d_viewer.apply_roi(XRangeROI(7000, 7100))

    # Subset 1 should follow Spectrum 2D viewer unit.
    # Subset 2 should follow Spectrum 1D viewer unit.
    subsets = specviz2d_helper.app.get_subsets()
    assert len(subsets) == 2
    s1 = subsets["Subset 1"]
    s2 = subsets["Subset 2"]
    assert s1.lower.unit == s1.upper.unit == u.pix
    assert s2.lower.unit == s2.upper.unit == u.AA


def test_parser_no_data(specviz2d_helper):
    with pytest.raises(ValueError, match='Must provide spectrum_2d or spectrum_1d'):
        specviz2d_helper.load_data()
