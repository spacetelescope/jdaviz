import os
import warnings

import pytest

from jdaviz.utils import (alpha_index, download_uri_to_path,
                          get_cloud_fits, cached_uri, escape_brackets,
                          has_wildcard, wildcard_match)
from astropy.io import fits

from jdaviz.conftest import FakeSpectrumListImporter


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
    uri = cached_uri("mast:jwst/product/jw01538-o161_t002-s000000001_nirspec_f290lp-g395h-s1600a1_s2d.fits")  # noqa: E501
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


class FakeObject:
    def __init__(self):
        pass


def test_escape_brackets():
    # Test that wildcard_match escapes brackets properly
    assert escape_brackets("") == ""
    assert escape_brackets("no brackets") == "no brackets"
    assert escape_brackets("some [brackets]") == "some [[]brackets[]]"
    assert escape_brackets("s[o]me [br]a[]ckets]") == "s[[]o[]]me [[]br[]]a[[][]]ckets[]]"


def test_has_wildcard():
    assert has_wildcard("") is False
    assert has_wildcard("no wildcards") is False
    assert has_wildcard("some * wildcard") is True
    assert has_wildcard("some ? wildcard") is True
    # Don't check for brackets anymore, just * and ?
    assert has_wildcard("some [brackets] wildcard") is False
    assert has_wildcard("some [brackets] and * wildcard") is True
    assert has_wildcard("some [brackets] and ? wildcard") is True
    assert has_wildcard("*") is True
    assert has_wildcard("?") is True


def test_wildcard_match_basic(deconfigged_helper, premade_spectrum_list):
    default_choices = ['some choice', 'some good choice', 'good choice', 'maybe a bad choice']
    test_obj = FakeObject()

    # No choices in obj or provided (choices is None)
    match_result = wildcard_match(test_obj, '*')
    assert match_result == '*'

    # No choices in obj or provided (choices is not None)
    match_result = wildcard_match(test_obj, '*', choices=[])
    assert match_result == ''

    # No choices in obj or provided, but multiselect is an attribute and false,
    # not all wildcards are *
    test_obj.multiselect = False
    match_result = wildcard_match(test_obj, '?*', choices=[])
    assert match_result == '?*'

    # Multiselect is not an attribute yet so we retain the value of the input string
    match_result = wildcard_match(test_obj, '*', choices=default_choices[0])
    assert match_result == ''

    test_obj.allow_multiselect = True
    # No choices in obj or provided, but multiselect is an attribute
    # and set to True inside the function
    match_result = wildcard_match(test_obj, '*', choices=[])
    assert match_result == []

    # No choices in obj or provided, but multiselect is an attribute
    # and set to True inside the function, value is a list of * wildcards
    match_result = wildcard_match(test_obj, ['*', '*'], choices=[])
    assert match_result == []

    # No choices in obj or provided, but multiselect is an attribute
    # and set to True inside the function, value list contains non-* wildcards
    match_result = wildcard_match(test_obj, ['*', '?', '*?'], choices=[])
    assert match_result == ['*', '?', '*?']

    # Add choices attribute, no matches
    test_obj.choices = default_choices
    match_result = wildcard_match(test_obj, 'not good*')
    assert match_result == ['not good*']

    # Test that the function kwarg `choices` overrides the object's choices attribute
    match_result = wildcard_match(test_obj, 'bad*', choices=default_choices[:-1])
    assert match_result == ['bad*']

    test_selections = {
        # Test all
        '*': default_choices,
        # Test no wildcard + wildcard
        ('some', 'some*'): ['some'] + default_choices[:2],
        # Test repeats
        ('*', '* good *'): default_choices,
        # Test single selection
        'some*': default_choices[:2],
        # Test multi-wildcard
        ('*', 'good*'): default_choices,
        # Test multi-selection
        ('some*', 'good*'): default_choices[:-1]}

    for selection, expected in test_selections.items():
        # Set and reset
        test_obj.multiselect = False
        match_result = wildcard_match(test_obj, selection)
        assert test_obj.multiselect is True
        assert match_result == expected

    # Making sure a stand-in for a SelectPluginComponent object with an attribute
    # that has `choices` works as expected
    fake_importer = FakeSpectrumListImporter(app=deconfigged_helper.app,
                                             resolver=deconfigged_helper.loaders['object']._obj,
                                             input=premade_spectrum_list)
    test_obj = fake_importer.sources

    """
    Left here for reference, premade_spectrum_list has 5 spectra:
    default_choices = ['1D Spectrum at index: 0',
                       '1D Spectrum at index: 1',
                       'Exposure 0, Source ID: 0000',
                       'Exposure 0, Source ID: 1111',
                       'Exposure 1, Source ID: 1111']
    """

    test_selections = {
        # Test all
        '*': test_obj.choices,
        # Test repeats
        ('*', '*:*'): test_obj.choices,
        # Test single selection
        '1D Spectrum at index: ?': test_obj.choices[:2],
        # Test multi-wildcard
        '*Exposure*': test_obj.choices[2:],
        # Test multi-selection
        ('*at index: 1', 'Exposure 0*'): test_obj.choices[1:-1]}

    for selection, expected in test_selections.items():
        # Reset
        test_obj.multiselect = False
        match_result = wildcard_match(test_obj, selection)
        assert test_obj.multiselect is True
        assert match_result == expected
