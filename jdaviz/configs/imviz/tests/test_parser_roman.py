import os
import pytest

CI = os.environ.get("CI", "").lower() in ("1", "true", "yes")

# NOTE: Since this is optional dependency, codecov coverage does not include this test module.
roman_datamodels = pytest.importorskip("roman_datamodels")

from gwcs import WCS as GWCS


@pytest.mark.parametrize(
    ('ext_list', 'n_dc'),
    [(None, 1),
     ('data', 1),
     (['data', 'var_poisson'], 2)])
@pytest.mark.skipif(CI, reason="Temporarily skipped failing imviz roman parser test in CI")
def test_roman_wfi_ext_options(deconfigged_helper, roman_imagemodel, ext_list, n_dc):
    deconfigged_helper.load(roman_imagemodel, data_label='roman_wfi_image_model', ext=ext_list)
    dc = deconfigged_helper._app.data_collection
    assert len(dc) == n_dc

    if ext_list == '*':
        ext_list = ('data', 'dq', 'err', 'var_poisson', 'var_rnoise')
    elif isinstance(ext_list, str):
        ext_list = (ext_list, )
    elif ext_list is None:
        ext_list = ('data', )

    for data, ext in zip(dc, ext_list):
        assert data.label == f'roman_wfi_image_model[{ext}]'
        assert data.shape == (20, 10)  # ny, nx
        assert isinstance(data.coords, GWCS)
