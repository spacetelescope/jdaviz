import numpy as np
import astropy.units as u
from astropy.nddata import NDData
from specreduce.tracing import FlatTrace

from jdaviz.core.loaders.importers.trace.trace import TraceImporter


def test_trace_importer_is_valid(deconfigged_helper, specviz2d_helper):
    """Test _check_is_valid for TraceImporter: success and failure cases."""

    resolver = deconfigged_helper.loaders['object']._obj
    trace = FlatTrace(image=NDData(np.ones((10, 20)), unit=u.Jy), trace_pos=5.0)

    def _create_importer(input_helper=deconfigged_helper,
                         input_resolver=resolver,
                         input_data=trace):
        return TraceImporter(app=input_helper._app,
                             resolver=input_resolver,
                             parser=None,
                             input=input_data)

    # Success: valid Trace with Spectral Extraction plugin available (specviz2d)
    resolver2d = specviz2d_helper.loaders['object']._obj
    importer = _create_importer(input_helper=specviz2d_helper, input_resolver=resolver2d)
    assert importer._check_is_valid() == ''

    # Failure: Trace without Spectral Extraction plugin (deconfigged has no plugin)
    importer = _create_importer()
    assert importer._check_is_valid() == 'Spectral Extraction plugin (for Trace) not available.'

    # Failure: non-Trace input
    importer = _create_importer(input_data='without_a_trace')
    assert importer._check_is_valid() == 'Input is not a Trace.'
