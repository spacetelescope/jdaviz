import pytest
from asdf.asdf import AsdfWarning
from astropy.utils.data import download_file

from specreduce import tracing
from specutils import Spectrum1D


@pytest.mark.remote_data
def test_plugin(specviz2d_helper):
    fn = download_file('https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits', cache=True)  # noqa

    with pytest.warns(AsdfWarning, match='jwextension'):
        specviz2d_helper.load_data(spectrum_2d=fn)

    pext = specviz2d_helper.app.get_tray_item_from_name('spectral-extraction')

    # test trace marks - won't be created until after opening the plugin
    sp2dv = specviz2d_helper.app.get_viewer('spectrum-2d-viewer')
    assert len(sp2dv.figure.marks) == 2

    specviz2d_helper.app.state.drawer = True
    tray_names = [ti['name'] for ti in specviz2d_helper.app.state.tray_items]
    plugin_index = tray_names.index('spectral-extraction')
    specviz2d_helper.app.state.tray_items_open = [plugin_index]
    assert len(sp2dv.figure.marks) == 20
    assert pext.marks['trace'].visible is True
    assert len(pext.marks['trace'].x) > 0

    # create FlatTrace
    pext.trace_pixel = 28
    trace = pext.create_trace()
    assert isinstance(trace, tracing.FlatTrace)

    # offset existing trace
    pext.trace_trace_selected = 'trace'
    pext.trace_offset = 2
    trace = pext.create_trace()
    assert isinstance(trace, tracing.ArrayTrace)

    # create KosmosTrace
    pext.trace_trace_selected = 'New Trace'
    pext.trace_type_selected = 'AutoTrace'
    trace = pext.create_trace()
    assert isinstance(trace, tracing.KosmosTrace)

    # 3 new trace objects should have been loaded and plotted in the spectrum-2d-viewer
    assert len(sp2dv.figure.marks) == 23

    # interact with background section, check marks
    pext.bg_separation = 3
    pext.bg_width = 1
    pext.bg_type_selected = 'TwoSided'
    for mark in ['bg1_center', 'bg2_center']:
        assert pext.marks[mark].visible is True
        assert len(pext.marks[mark].x) > 0
    pext.bg_type_selected = 'Trace'
    assert len(pext.marks['bg1_center'].x) == 0
    assert len(pext.marks['bg2_center'].x) == 0
    assert len(pext.marks['bg1_lower'].x) > 0
    pext.bg_type_selected = 'OneSided'
    # only bg1 is populated for OneSided
    assert len(pext.marks['bg1_center'].x) > 0
    assert len(pext.marks['bg2_center'].x) == 0

    # create background image
    pext.bg_trace_selected = 'Manual'
    pext.bg_trace_pixel = 20
    pext.bg_separation = -8
    bg = pext.create_bg()
    assert isinstance(bg, Spectrum1D)
    bg_sub = pext.create_bg_sub()
    assert isinstance(bg_sub, Spectrum1D)

    # interact with extraction section, check marks
    pext.ext_width = 1
    for mark in ['bg1_center', 'bg2_center']:
        assert pext.marks[mark].visible is False
    for mark in ['ext_lower', 'ext_upper']:
        assert pext.marks[mark].visible is True
        assert len(pext.marks[mark].x) > 0

    # create subtracted spectrum
    sp_ext = pext.create_extract()
    assert isinstance(sp_ext, Spectrum1D)
