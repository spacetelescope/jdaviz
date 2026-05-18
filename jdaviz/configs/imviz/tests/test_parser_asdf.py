import asdf
import numpy as np
import pytest

import astropy.units as u

from jdaviz.configs.imviz.tests.utils import create_example_gwcs
from jdaviz.configs.imviz.plugins.parsers import HAS_ROMAN_DATAMODELS


def test_asdf_not_rdm(imviz_helper):
    # test support for ASDF files that look like Roman files
    # for users with or without roman_datamodels. In this case,
    # we've assigned units to the image data:
    in_unit = u.Jy
    in_data = np.arange(16, dtype=np.float32).reshape((4, 4)) * in_unit
    tree = {
        'roman': {
            'data': in_data,
            'meta': {
                'wcs': create_example_gwcs((4, 4))
            },
        },
    }

    af = asdf.AsdfFile(tree=tree)
    imviz_helper.load(af)
    out_component = imviz_helper._app.data_collection[0].get_component('DATA')
    np.testing.assert_array_equal(in_data.value, out_component.data)
    assert str(in_unit) == out_component.units


@pytest.mark.skipif(not HAS_ROMAN_DATAMODELS, reason="roman_datamodels is not installed")
def test_asdf_via_rdm(imviz_helper, roman_imagemodel):
    # test support for ASDF files as roman_datamodels ImageModels. In this
    # case, the data don't have units.
    imviz_helper.load(roman_imagemodel)
    out_component = imviz_helper._app.data_collection[0].get_component('DATA')
    np.testing.assert_array_equal(roman_imagemodel.data, out_component.data)
