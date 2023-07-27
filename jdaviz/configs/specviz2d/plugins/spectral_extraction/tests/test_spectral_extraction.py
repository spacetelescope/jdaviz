import gwcs
import pytest
from astropy.utils.data import download_file
from packaging.version import Version
from specreduce import tracing, background, extract
from specutils import Spectrum1D

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
    assert len(sp2dv.figure.marks) == 2

    pext.keep_active = True
    assert len(sp2dv.figure.marks) == 11
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

    # 3 new trace objects should have been loaded and plotted in the spectrum-2d-viewer
    assert len(sp2dv.figure.marks) == 14

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
    assert "override label 2" in pext.bg_sub_add_results.__repr__()
    assert "override label 2" in pext.bg_sub_add_results._obj.auto_label.__repr__()

    pext.export_bg_sub(add_data=True)
    assert 'override label 2' in pext.ext_dataset.choices

    # test setting auto label
    pext.bg_sub_add_results.auto = True


@pytest.mark.skip(reason='filenames changed')
@pytest.mark.remote_data
@pytest.mark.skipif(GWCS_LT_0_18_1, reason='Needs GWCS 0.18.1 or later')
def test_spectrum_on_top(specviz2d_helper):
    fn = download_file('https://mast.stsci.edu/api/v0.1/Download/file/?uri=mast:jwst/product/jw01529-o004_t002_miri_p750l_s2d.fits', cache=True)  # noqa

    specviz2d_helper.load_data(spectrum_2d=fn)

    pext = specviz2d_helper.app.get_tray_item_from_name('spectral-extraction')
    assert pext.bg_type_selected == 'OneSided'
    assert pext.bg_separation < 0
