import gwcs
import pytest
from astropy.modeling import models
from astropy.nddata import VarianceUncertainty
from astropy.tests.helper import assert_quantity_allclose
import astropy.units as u
from astropy.utils.data import download_file
import numpy as np
from packaging.version import Version
from specreduce import tracing, background, extract
from specutils import Spectrum1D

from jdaviz.core.custom_units_and_equivs import SPEC_PHOTON_FLUX_DENSITY_UNITS

GWCS_LT_0_18_1 = Version(gwcs.__version__) < Version('0.18.1')


@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore')
def test_plugin(specviz2d_helper):
    # TODO: Change back to smaller number (30?) when ITSD is convinced it is them and not us.
    #       Help desk ticket INC0183598, J. Quick.
    fn = download_file('https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits',
                       cache=True, timeout=100)

    specviz2d_helper.load_data(spectrum_2d=fn)

    pext = specviz2d_helper.app.get_tray_item_from_name('spectral-extraction')

    # test trace marks - won't be created until after opening the plugin
    sp2dv = specviz2d_helper.app.get_viewer('spectrum-2d-viewer')
    assert len(sp2dv.figure.marks) == 3

    pext.keep_active = True
    assert len(sp2dv.figure.marks) == 12
    assert pext.marks['trace'].visible is True
    assert len(pext.marks['trace'].x) > 0

    # create FlatTrace
    pext.trace_type_selected = 'Flat'
    pext.trace_pixel = 28
    trace = pext.export_trace(add_data=True)
    assert isinstance(trace, tracing.FlatTrace)
    assert trace.trace_pos == 28
    trace.trace_pos = 27
    pext.import_trace(trace)
    assert pext.trace_pixel == 27

    # offset existing trace
    pext.trace_trace_selected = 'trace'
    pext.trace_offset = 2
    trace = pext.export_trace(add_data=True)  # overwrite
    assert isinstance(trace, tracing.FlatTrace)

    # create FitTrace
    pext.trace_trace_selected = 'New Trace'
    pext.trace_type_selected = 'Polynomial'
    trace = pext.export_trace(add_data=True)
    assert isinstance(trace, tracing.FitTrace)
    assert trace.guess == 27
    trace = pext.export_trace(trace_pixel=26, add_data=False)
    assert trace.guess == 26
    trace.guess = 28
    pext.import_trace(trace)
    assert pext.trace_pixel == 28

    # offset existing trace
    pext.trace_trace_selected = 'trace'
    pext.trace_offset = 2
    trace = pext.export_trace(add_data=True)  # overwrite
    assert isinstance(trace, tracing.ArrayTrace)

    # TODO: Investigate extra hidden mark from glue-jupyter, see
    # https://github.com/spacetelescope/jdaviz/pull/2478#issuecomment-1731864411
    # 3 new trace objects should have been loaded and plotted in the spectrum-2d-viewer
    assert len(sp2dv.figure.marks) == 16

    # interact with background section, check marks
    pext.trace_trace_selected = 'New Trace'
    pext.trace_type_selected = 'Flat'
    pext.bg_separation = 5
    pext.bg_width = 3
    pext.bg_type_selected = 'TwoSided'
    for mark in ['bg1_center', 'bg2_center']:
        assert pext.marks[mark].visible is True
        assert len(pext.marks[mark].x) > 0
    bg = pext.export_bg()
    pext.import_bg(bg)
    assert pext.bg_type_selected == 'TwoSided'

    pext.bg_type_selected = 'Manual'
    assert len(pext.marks['bg1_center'].x) == 0
    assert len(pext.marks['bg2_center'].x) == 0
    assert len(pext.marks['bg1_lower'].x) > 0

    pext.bg_type_selected = 'OneSided'
    # only bg1 is populated for OneSided
    assert len(pext.marks['bg1_center'].x) > 0
    assert len(pext.marks['bg2_center'].x) == 0

    # create background image
    pext.bg_separation = 4
    bg = pext.export_bg()
    assert isinstance(bg, background.Background)
    assert len(bg.traces) == 1
    assert bg.traces[0].trace[0] == 28 + 4
    assert bg.width == 3
    bg = pext.export_bg(bg_width=3.3)
    assert bg.width == 3.3
    bg.width = 4
    pext.import_bg(bg)
    assert pext.bg_width == 4
    bg_img = pext.export_bg_img()
    assert isinstance(bg_img, Spectrum1D)
    bg_spec = pext.export_bg_spectrum()
    assert isinstance(bg_spec, Spectrum1D)
    bg_sub = pext.export_bg_sub()
    assert isinstance(bg_sub, Spectrum1D)

    # interact with extraction section, check marks
    pext.ext_width = 1
    for mark in ['bg1_center', 'bg2_center']:
        assert pext.marks[mark].visible is False
    for mark in ['ext_lower', 'ext_upper']:
        assert pext.marks[mark].visible is True
        assert len(pext.marks[mark].x) > 0

    # create subtracted spectrum
    ext = pext.export_extract(ext_width=3)
    assert isinstance(ext, extract.BoxcarExtract)
    assert ext.width == 3
    ext.width = 2
    pext.import_extract(ext)
    assert pext.ext_width == 2
    sp_ext = pext.export_extract_spectrum()
    assert isinstance(sp_ext, Spectrum1D)

    pext.ext_type_selected = 'Horne'
    sp_ext = pext.export_extract_spectrum()
    assert isinstance(sp_ext, Spectrum1D)

    # test API calls
    for step in ['trace', 'bg', 'ext']:
        pext.update_marks(step)

    # test exception handling
    pext.trace_type = 'Polynomial'
    pext.bg_type_selected = 'TwoSided'
    pext.bg_separation = 1
    pext.bg_width = 5
    assert len(pext.ext_specreduce_err) > 0
    pext.bg_results_label = 'should not be created'
    pext.vue_create_bg_img()
    assert 'should not be created' not in [d.label for d in specviz2d_helper.app.data_collection]

    with pytest.raises(ValueError):
        pext.export_extract(invalid_kwarg=5)


@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore')
def test_user_api(specviz2d_helper):
    fn = download_file('https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits', cache=True)  # noqa

    specviz2d_helper.load_data(spectrum_2d=fn)

    pext = specviz2d_helper.plugins['Spectral Extraction']
    pext.keep_active = True

    # test that setting a string to an AddResults object redirects to the label
    pext.bg_sub_add_results = 'override label'
    assert pext.bg_sub_add_results.label == 'override label'
    pext.bg_sub_add_results.label = 'override label 2'
    assert "override label 2" in pext.bg_sub_add_results._obj.__repr__()
    assert "override label 2" in pext.bg_sub_add_results._obj.auto_label.__repr__()

    pext.export_bg_sub(add_data=True)
    assert 'override label 2' in pext.ext_dataset.choices

    # test setting auto label
    pext.bg_sub_add_results.auto = True


@pytest.mark.remote_data
@pytest.mark.skipif(GWCS_LT_0_18_1, reason='Needs GWCS 0.18.1 or later')
def test_spectrum_on_top(specviz2d_helper):
    fn = download_file('https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:jwst/product/jw01538-o161_s000000001_nirspec_f290lp-g395h-s1600a1_s2d.fits', cache=True)  # noqa

    specviz2d_helper.load_data(spectrum_2d=fn)

    pext = specviz2d_helper.app.get_tray_item_from_name('spectral-extraction')
    pext.trace_pixel = 14.2
    assert pext.bg_type_selected == 'OneSided'
    np.testing.assert_allclose(pext.bg_separation, 6)


@pytest.mark.filterwarnings('ignore')
def test_horne_extract_self_profile(specviz2d_helper):

    spec2d = np.zeros((40, 100))
    spec2dvar = np.ones((40, 100))

    for ii in range(spec2d.shape[1]):
        mgaus = models.Gaussian1D(amplitude=10,
                                  mean=(9.+(20/spec2d.shape[1])*ii),
                                  stddev=2)
        rg = np.arange(0, spec2d.shape[0], 1)
        gaus = mgaus(rg)
        spec2d[:, ii] = gaus

    wave = np.arange(0, spec2d.shape[1], 1)
    objectspec = Spectrum1D(spectral_axis=wave*u.m,
                            flux=spec2d*u.Jy,
                            uncertainty=VarianceUncertainty(spec2dvar*u.Jy*u.Jy))

    specviz2d_helper.load_data(objectspec)
    pext = specviz2d_helper.app.get_tray_item_from_name('spectral-extraction')

    trace_fit = tracing.FitTrace(objectspec,
                                 trace_model=models.Polynomial1D(degree=1),
                                 window=13, peak_method='gaussian', guess=20)
    pext.import_trace(trace_fit)

    pext.ext_type.selected = "Horne"
    pext.horne_ext_profile.selected = "Self (interpolated)"

    # check that correct defaults are set
    assert pext.self_prof_n_bins == 10
    assert pext.self_prof_interp_degree_x == 1
    assert pext.self_prof_interp_degree_y == 1

    sp_ext = pext.export_extract_spectrum()

    bg_sub = pext.export_bg_sub()

    extract_horne_interp = extract.HorneExtract(bg_sub, trace_fit,
                                                spatial_profile='interpolated_profile')

    assert_quantity_allclose(extract_horne_interp.spectrum.flux, sp_ext.flux)

    # now try changing from defaults
    pext.self_prof_n_bins = 5
    pext.self_prof_interp_degree_x = 2
    pext.self_prof_interp_degree_y = 2

    sp_ext = pext.export_extract_spectrum()
    bg_sub = pext.export_bg_sub()

    extract_horne_interp = extract.HorneExtract(bg_sub, trace_fit,
                                                spatial_profile={'name': 'interpolated_profile',
                                                                 'n_bins_interpolated_profile': 5,
                                                                 'interp_degree': (2, 2)})

    assert_quantity_allclose(extract_horne_interp.spectrum.flux, sp_ext.flux)

    # test that correct errors are raised
    pext.self_prof_n_bins = 0
    with pytest.raises(ValueError, match='must be greater than 0'):
        sp_ext = pext.export_extract_spectrum()

    pext.self_prof_n_bins = 1
    pext.self_prof_interp_degree_x = 0
    with pytest.raises(ValueError, match='must be greater than 0'):
        sp_ext = pext.export_extract_spectrum()

    pext.self_prof_interp_degree_x = 1
    pext.self_prof_interp_degree_y = 0
    with pytest.raises(ValueError, match='`self_prof_interp_degree_y` must be greater than 0.'):
        sp_ext = pext.export_extract_spectrum()


def test_spectral_extraction_flux_unit_conversions(specviz2d_helper, mos_spectrum2d):
    specviz2d_helper.load_data(mos_spectrum2d)

    uc = specviz2d_helper.plugins["Unit Conversion"]
    pext = specviz2d_helper.plugins['Spectral Extraction']

    for new_flux_unit in SPEC_PHOTON_FLUX_DENSITY_UNITS:
        # iterate through flux units verifying that selected object/spectrum is obtained using
        # display units
        uc.flux_unit.selected = new_flux_unit

        exported_bg = pext.export_bg()
        assert exported_bg.image._unit == specviz2d_helper.app._get_display_unit('flux')

        exported_bg_img = pext.export_bg_img()
        assert exported_bg_img._unit == specviz2d_helper.app._get_display_unit('flux')

        exported_bg_sub = pext.export_bg_sub()
        assert exported_bg_sub._unit == specviz2d_helper.app._get_display_unit('flux')

        exported_extract_spectrum = pext.export_extract_spectrum()
        assert exported_extract_spectrum._unit == specviz2d_helper.app._get_display_unit('flux')

        exported_extract = pext.export_extract()
        assert exported_extract.image._unit == specviz2d_helper.app._get_display_unit('flux')
