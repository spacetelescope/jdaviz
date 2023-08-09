import asdf
import numpy as np
import astropy.units as u

from jdaviz.configs.imviz.tests.utils import create_example_gwcs


def test_asdf_not_rdm(imviz_helper):
    # test support for ASDF files that look like Roman files
    # for users with or without roman_datamodels:
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
    imviz_helper.load_data(af)
    out_component = imviz_helper.app.data_collection[0].get_component('DATA')
    np.testing.assert_array_equal(in_data.value, out_component.data)
    assert str(in_unit) == out_component.units
