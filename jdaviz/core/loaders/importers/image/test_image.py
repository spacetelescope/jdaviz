import pytest

from jdaviz.core.loaders.importers.image.image import ImageImporter
from jdaviz.configs.imviz.plugins.parsers import HAS_ROMAN_DATAMODELS


@pytest.mark.skipif(not HAS_ROMAN_DATAMODELS, reason="roman_datamodels is not installed")
def test_roman_level_3(deconfigged_helper, roman_level_3_mosaic):
    resolver = deconfigged_helper.loaders['object']._obj

    def _create_importer(input_data=None):
        return ImageImporter(app=deconfigged_helper._app,
                             resolver=resolver, parser=None,
                             input=input_data)

    # check that the importer works on Roman L3s
    importer = _create_importer(input_data=roman_level_3_mosaic)
    assert importer.is_valid
