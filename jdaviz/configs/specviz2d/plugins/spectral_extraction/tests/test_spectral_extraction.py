import pytest
from asdf.asdf import AsdfWarning
from astropy.utils.data import download_file

from specreduce import tracing


@pytest.mark.remote_data
def test_plugin(specviz2d_helper):
    fn = download_file('https://stsci.box.com/shared/static/exnkul627fcuhy5akf2gswytud5tazmw.fits', cache=True)  # noqa

    with pytest.warns(AsdfWarning, match='jwextension'):
        specviz2d_helper.load_data(spectrum_2d=fn)

    pext = specviz2d_helper.app.get_tray_item_from_name('spectral-extraction')

    trace = pext.create_trace()
    assert isinstance(trace, tracing.FlatTrace)

    pext.trace_trace_selected = 'trace'
    pext.trace_offset = 2
    trace = pext.create_trace()
    assert isinstance(trace, tracing.FlatTrace)

    pext.trace_trace_selected = 'New Trace'
    pext.trace_type_selected = 'AutoTrace'
    trace = pext.create_trace()
    assert isinstance(trace, tracing.KosmosTrace)
