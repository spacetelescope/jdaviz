from jdaviz.core.loaders.importers.ramp_integration.ramp_integration import RampIntegrationImporter


def test_ramp_integration_importer_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in RampIntegrationImporter._check_is_valid."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Non-array, non-NDDataArray input
    importer = RampIntegrationImporter(app=deconfigged_helper._app,
                                       resolver=resolver, parser=None,
                                       input='not_an_array')
    assert importer._check_is_valid() == 'Input must be a numpy array or NDDataArray.'
