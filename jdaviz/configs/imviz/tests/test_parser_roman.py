import pytest
import shutil

from astropy.utils.data import download_file
from gwcs import WCS as GWCS
from jdaviz.configs.imviz.plugins.parsers import HAS_ROMAN_DATAMODELS


@pytest.mark.skipif(not HAS_ROMAN_DATAMODELS, reason="requires optional roman deps")
@pytest.mark.parametrize(
    ('ext_list', 'n_dc'),
    [(None, 1),
     ('data', 1),
     (['data', 'var_rnoise'], 2)])
def test_roman_wfi_ext_options(imviz_helper, roman_imagemodel, ext_list, n_dc):
    imviz_helper.load_data(roman_imagemodel, data_label='roman_wfi_image_model', ext=ext_list)
    dc = imviz_helper.app.data_collection
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


@pytest.mark.remote_data
@pytest.mark.usefixtures('_jail')
@pytest.mark.skipif(HAS_ROMAN_DATAMODELS,
                    reason="requires asdf, but assumes roman_datamodels not installed")
def test_roman_wfi_ext_no_rdm(imviz_helper):
    # check how the file is loaded with roman_datamodels

    # this is a Level 2 image for SCA01 from B17.
    file_name = '9l76vqikqfrkv2ssr8za2bo8gi4ghc8t.asdf'
    url = f'https://stsci.box.com/shared/static/{file_name}'
    path = download_file(url)

    # copy the file out of the astropy cache to test the parser:
    shutil.copyfile(path, file_name)

    with (
        # helpful warning for the user:
        pytest.raises(UserWarning, match="should be opened with the `roman_datamodels` package"),

        # this will ultimately fail on an import if the binary is compressed with lz4:
        pytest.raises(ImportError, match="lz4 library in not installed")
    ):
        imviz_helper.load_data(file_name, data_label='roman_wfi_image_model')
