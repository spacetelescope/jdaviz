import os
import warnings
import re

import pytest

from jdaviz.utils import alpha_index, download_uri_to_path, get_cloud_fits, cached_uri
from astropy.io import fits


@pytest.mark.parametrize("test_input,expected", [(0, 'a'), (1, 'b'), (25, 'z'), (26, 'aa'),
                                                 (701, 'zz'), (702, '{a')])
def test_alpha_index(test_input, expected):
    assert alpha_index(test_input) == expected


def test_alpha_index_exceptions():
    with pytest.raises(TypeError, match="index must be an integer"):
        alpha_index(4.2)
    with pytest.raises(ValueError, match="index must be positive"):
        alpha_index(-1)


def test_uri_to_download_bad_scheme(imviz_helper):
    uri = "file://path/to/file.fits"
    with pytest.raises(ValueError, match="no valid loaders found for input"):
        imviz_helper.load_data(uri)


@pytest.mark.remote_data
def test_uri_to_download_nonexistent_mast_file(imviz_helper):
    # this validates as a mast uri but doesn't actually exist on mast:
    uri = "mast:JWST/product/jw00000-no-file-here.fits"
    with pytest.raises(ValueError, match='Failed query for URI'):
        # NOTE: this test will attempt to reach out to MAST via astroquery
        # even if cache is available.
        imviz_helper.load_data(uri, cache=False)


@pytest.mark.remote_data
def test_url_to_download_imviz_local_path_warning(imviz_helper):
    url = "https://www.astropy.org/astropy-data/tutorials/FITS-images/HorseHead.fits"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        imviz_helper.load_data(url, cache=True, local_path='horsehead.fits')


def test_uri_to_download_specviz_local_path_check():
    # NOTE: do not use cached_uri here since no download should occur
    uri = "mast:JWST/product/jw02732-c1001_t004_miri_ch1-short_x1d.fits"
    local_path = download_uri_to_path(uri, cache=False, dryrun=True)  # No download

    # Wrong: '.\\JWST/product/jw02732-c1001_t004_miri_ch1-short_x1d.fits'
    # Correct:  '.\\jw02732-c1001_t004_miri_ch1-short_x1d.fits'
    assert local_path == os.path.join(os.curdir, "jw02732-c1001_t004_miri_ch1-short_x1d.fits")  # noqa: E501


@pytest.mark.remote_data
def test_uri_to_download_specviz(specviz_helper):
    uri = cached_uri("mast:JWST/product/jw02732-c1001_t004_miri_ch1-short_x1d.fits")
    specviz_helper.load_data(uri, cache=True)


@pytest.mark.remote_data
def test_uri_to_download_specviz2d(specviz2d_helper):
    uri = cached_uri("mast:jwst/product/jw01538-o161_s000000001_nirspec_f290lp-g395h-s1600a1_s2d.fits")  # noqa: E501
    specviz2d_helper.load_data(uri, cache=True)


@pytest.mark.remote_data
def test_load_s3_fits(imviz_helper):
    """Test loading a JWST FITS file from an S3 URI into Imviz."""
    s3_uri = "s3://stpubdata/jwst/public/jw02727/L3/t/o002/jw02727-o002_t062_nircam_clear-f277w_i2d.fits"  # noqa: E501
    imviz_helper.load_data(s3_uri)
    assert len(imviz_helper.app.data_collection) > 0


@pytest.mark.remote_data
def test_get_cloud_fits_ext():
    s3_uri = "s3://stpubdata/jwst/public/jw02727/L3/t/o002/jw02727-o002_t062_nircam_clear-f277w_i2d.fits"  # noqa: E501
    hdul = get_cloud_fits(s3_uri)
    assert isinstance(hdul, fits.HDUList)

    hdul = get_cloud_fits(s3_uri, ext="SCI")
    assert isinstance(hdul, fits.HDUList)

    hdul = get_cloud_fits(s3_uri, ext=["SCI"])
    assert isinstance(hdul, fits.HDUList)

def test_wildcard_matching_sources(specviz_helper, premade_spectrum_list):
    """
    Test wildcard matching for source selection in Specviz. This tests setting
    the selection directly as opposed to using ``load``, via ``ldr.importer.sources``
    (whereas in the following test this is done through ``user_api.extension``, same idea).
    """
    default_choices = ['1D Spectrum at index: 0',
                       '1D Spectrum at index: 1',
                       'Exposure 0, Source ID: 0000',
                       'Exposure 0, Source ID: 1111',
                       'Exposure 1, Source ID: 1111']

    # Testing directly
    ldr = specviz_helper.loaders['object']
    ldr.object = premade_spectrum_list
    selection_obj = ldr.importer.sources
    assert selection_obj.selected == []

    assert selection_obj.choices == default_choices
    # This should get set to True automatically when multiple selections are made
    selection_obj.multiselect = False

    err_str1 = "not all items in"
    err_str2 = f"are one of {selection_obj.choices}, reverting selection to []"
    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['bad *'] {err_str2}")):
        ldr.importer.sources = 'bad *'

    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['bad *', '* result'] {err_str2}")):
        ldr.importer.sources = ['bad *', '* result']

    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['another', 'bad * result'] {err_str2}")):
        ldr.importer.sources = ['another', 'bad * result']

    # Check that selected is still/reverted successfully to []
    assert selection_obj.selected == []

    test_selections = {
        # Test all
        '*': selection_obj.choices,
        # Test repeats
        ('*', '*:*'): selection_obj.choices,
        # Test single selection
        '1D Spectrum at index:*': selection_obj.choices[:2],
        # Test multi-wildcard
        '*Exposure*': selection_obj.choices[2:],
        # Test multi-selection
        ('*at index: 1', 'Exposure 0*'): selection_obj.choices[1:-1]}

    for selection, expected in test_selections.items():
        ldr.importer.sources = selection
        assert selection_obj.multiselect is True
        assert selection_obj.selected == expected
        # Reset
        selection_obj.selected = []
        selection_obj.multiselect = False


def test_wildcard_matching_extension(imviz_helper, multi_extension_image_hdu_wcs):
    """
    Test wildcard matching for source selection in Specviz. This tests setting
    the selection directly as opposed to using ``load``, via
    ``ldr.importer._obj.user_api.extensions`` (whereas in the previous test this is
    done through ``user_api.sources``, same idea).
    """
    default_choices = ['1: [SCI,1]',
                       '2: [MASK,1]',
                       '3: [ERR,1]',
                       '4: [DQ,1]']

    # Testing directly
    ldr = imviz_helper.loaders['object']
    ldr.object = multi_extension_image_hdu_wcs
    selection_obj = ldr.importer.extension

    # Default selection
    assert selection_obj.selected == [default_choices[0]]

    # Resetting to []
    # Note this can't be done by setting selected = [], is this intentional?
    selection_obj.selected.pop(0)
    assert selection_obj.selected == []

    assert selection_obj.choices == default_choices
    # This should get set to True automatically when multiple selections are made
    selection_obj.multiselect = False

    err_str1 = "not all items in"
    err_str2 = f"are one of {selection_obj.choices}, reverting selection to []"
    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['bad *'] {err_str2}")):
        ldr.importer._obj.user_api.extension = 'bad *'

    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['bad *', '* result'] {err_str2}")):
        ldr.importer._obj.user_api.extension = ['bad *', '* result']

    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['another', 'bad * result'] {err_str2}")):
        ldr.importer._obj.user_api.extension = ['another', 'bad * result']

    # Check that selected is still/reverted successfully to []
    assert selection_obj.selected == []

    test_selections = {
        # Test all
        '*': selection_obj.choices,
        # Test repeats
        ('*', '*:*'): selection_obj.choices,
        # Test single selection
        '1:*': [selection_obj.choices[0]],
        # Test multi-wildcard
        '*S*': selection_obj.choices[:2],
        # Test multi-selection
        ('*ERR*', '*DQ*'): selection_obj.choices[2:]}

    for selection, expected in test_selections.items():
        ldr.importer._obj.user_api.extension = selection
        assert selection_obj.multiselect is True
        assert selection_obj.selected == expected
        # Reset
        selection_obj.selected = []
        selection_obj.multiselect = False


@pytest.mark.parametrize(
    ("selection", "matches"), [
        ('*', (0, 1, 2, 3)),
        (('*', '*:*'), (0, 1, 2, 3)),
        ('1:*', (0,)),
        ('*S*', (0, 1)),
        (('*ERR*', '*DQ*'), (2, 3))])
def test_wildcard_matching_through_load(imviz_helper, multi_extension_image_hdu_wcs,
                                        selection, matches):
    data_labels = ['Image[SCI,1]',
                   'Image[MASK,1]',
                   'Image[ERR,1]',
                   'Image[DQ,1]']

    # Through load
    imviz_helper.load(multi_extension_image_hdu_wcs, extension=selection)
    assert imviz_helper.data_labels == [data_labels[i] for i in matches]