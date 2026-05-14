import numpy as np
import astropy.units as u
from astropy.nddata import NDData
from specreduce.tracing import FlatTrace

from jdaviz.core.loaders.importers.trace.trace import TraceImporter


def test_trace_importer_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in TraceImporter._check_is_valid."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Non-Trace input should be rejected
    importer = TraceImporter(app=deconfigged_helper._app,
                             resolver=resolver, parser=None,
                             input='not_a_trace')
    assert importer._check_is_valid() == 'Input is not a Trace.'

    # When Spectral Extraction plugin is not available, Trace is rejected
    trace = FlatTrace(image=NDData(np.ones((10, 20)), unit=u.Jy),
                      trace_pos=5.0)
    importer = TraceImporter(app=deconfigged_helper._app,
                             resolver=resolver, parser=None,
                             input=trace)
    assert importer._check_is_valid() == 'Spectral Extraction plugin (for Trace) not available.'
