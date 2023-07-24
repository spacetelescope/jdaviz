import pytest

# NOTE: Since this is optional dependency, codecov coverage does not include this test module.
roman_datamodels = pytest.importorskip("roman_datamodels")

from astropy.utils.data import get_pkg_data_filename
from gwcs import WCS as GWCS


@pytest.mark.parametrize(
    ('ext_list', 'n_dc'),
    [(None, 5),
     ('data', 1),
     (['data', 'var_rnoise'], 2)])
def test_roman_wfi_ext_options(imviz_helper, ext_list, n_dc):
    filename = get_pkg_data_filename('data/roman_wfi_image_model.asdf')
    imviz_helper.load_data(filename, ext=ext_list)
    dc = imviz_helper.app.data_collection
    assert len(dc) == n_dc

    if ext_list is None:
        ext_list = ('data', 'dq', 'err', 'var_poisson', 'var_rnoise')
    elif isinstance(ext_list, str):
        ext_list = (ext_list, )

    for data, ext in zip(dc, ext_list):
        assert data.label == f'roman_wfi_image_model[{ext.upper()}]'
        assert data.shape == (20, 10)  # ny, nx
        assert isinstance(data.coords, GWCS)
