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

    pext.open_in_tray()
    assert len(sp2dv.figure.marks) == 11
    assert pext.marks['trace'].visible is True
    assert len(pext.marks['trace'].x) > 0

    # create FlatTrace
    pext.trace_type_selected = 'Flat'
    pext.trace_pixel = 28
    trace = pext.create_trace()
    assert isinstance(trace, tracing.FlatTrace)

    # create KosmosTrace
    pext.trace_type_selected = 'Auto'
    trace = pext.create_trace()
    assert isinstance(trace, tracing.KosmosTrace)

    # interact with background section, check marks
    pext.trace_type_selected = 'Flat'
    pext.bg_separation = 5
    pext.bg_width = 3
    pext.bg_type_selected = 'TwoSided'
    for mark in ['bg1_center', 'bg2_center']:
        assert pext.marks[mark].visible is True
        assert len(pext.marks[mark].x) > 0
    pext.bg_type_selected = 'Manual'
    assert len(pext.marks['bg1_center'].x) == 0
    assert len(pext.marks['bg2_center'].x) == 0
    assert len(pext.marks['bg1_lower'].x) > 0
    pext.bg_type_selected = 'OneSided'
    # only bg1 is populated for OneSided
    assert len(pext.marks['bg1_center'].x) > 0
    assert len(pext.marks['bg2_center'].x) == 0

    # create background image
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

    # test exception handling
    pext.trace_type = 'Auto'
    pext.bg_type_selected = 'TwoSided'
    pext.bg_separation = 1
    pext.bg_width = 5
    assert len(pext.ext_specreduce_err) > 0
    pext.bg_results_label = 'should not be created'
    pext.vue_create_bg()
    assert 'should not be created' not in [d.label for d in specviz2d_helper.app.data_collection]
