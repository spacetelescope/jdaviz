import numpy as np

from jdaviz.core.loaders.importers.ramp_integration.ramp_integration import RampIntegrationImporter


def test_ramp_integration_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for RampIntegrationImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Success: numpy array input
    importer = RampIntegrationImporter(app=deconfigged_helper._app,
                                       resolver=resolver, parser=None,
                                       input=np.ones((3, 4, 5)))
    assert importer._check_is_valid() == ''

    # Failure: non-array, non-NDDataArray input
    importer = RampIntegrationImporter(app=deconfigged_helper._app,
                                       resolver=resolver, parser=None,
                                       input='not_an_array')
    assert importer._check_is_valid() == 'Input must be a numpy array or NDDataArray.'
