from astropy.io.fits import PrimaryHDU
from ..plugins.parsers import _get_source_names_by_hdu, FALLBACK_NAME


def test_hdu_source_name_extract_SOURCEID():
    hdu = PrimaryHDU()
    hdu.header['SOURCEID'] = 'Target 1 SOURCEID'
    assert _get_source_names_by_hdu([hdu]) == ['Target 1 SOURCEID']

    hdu2 = PrimaryHDU()
    hdu2.header['SOURCEID'] = 'Target 2 SOURCEID'
    assert _get_source_names_by_hdu([hdu, hdu2]) == ['Target 1 SOURCEID', 'Target 2 SOURCEID']


def test_hdu_source_name_extract_OBJECT():
    hdu = PrimaryHDU()
    hdu.header['OBJECT'] = 'Target 1 OBJECT'
    assert _get_source_names_by_hdu([hdu]) == ['Target 1 OBJECT']

    hdu2 = PrimaryHDU()
    hdu2.header['OBJECT'] = 'Target 2 OBJECT'
    assert _get_source_names_by_hdu([hdu, hdu2]) == ['Target 1 OBJECT', 'Target 2 OBJECT']


def test_hdu_source_name_extract_priority():
    hdu = PrimaryHDU()
    hdu.header['SOURCEID'] = 'Target 1 SOURCEID'
    hdu.header['OBJECT'] = 'Target 1 OBJECT'
    assert _get_source_names_by_hdu([hdu]) == ['Target 1 SOURCEID']

    hdu2 = PrimaryHDU()
    hdu2.header['SOURCEID'] = 'Target 2 SOURCEID'
    hdu2.header['OBJECT'] = 'Target 2 OBJECT'
    assert _get_source_names_by_hdu([hdu, hdu2]) == ['Target 1 SOURCEID', 'Target 2 SOURCEID']


def test_hdu_source_name_extract_priority_mixed():
    hdu = PrimaryHDU()
    hdu.header['SOURCEID'] = 'Target 1 SOURCEID'
    hdu.header['OBJECT'] = 'Target 1 OBJECT'
    assert _get_source_names_by_hdu([hdu]) == ['Target 1 SOURCEID']

    hdu2 = PrimaryHDU()
    hdu2.header['OBJECT'] = 'Target 2 OBJECT'
    assert _get_source_names_by_hdu([hdu, hdu2]) == ['Target 1 SOURCEID', 'Target 2 OBJECT']


def test_hdu_source_name_extract_empty_fallback():
    hdu = PrimaryHDU()
    assert _get_source_names_by_hdu([hdu]) == [FALLBACK_NAME]
    assert _get_source_names_by_hdu([hdu, hdu]) == [FALLBACK_NAME, FALLBACK_NAME]


def test_hdu_source_name_extract_single_filename_fallback():
    hdu = PrimaryHDU()
    assert _get_source_names_by_hdu([hdu], "/path/to/test_file.fits") == ['test_file.fits']
    assert _get_source_names_by_hdu([hdu, hdu],
                                    "/path/to/test_file.fits"
                                    ) == ['test_file.fits', 'test_file.fits']


def test_hdu_source_name_extract_filename_fallback():
    hdu = PrimaryHDU()
    assert _get_source_names_by_hdu([hdu], ["/path/to/test_file.fits"]) == ['test_file.fits']
    assert _get_source_names_by_hdu([hdu, hdu],
                                    ["/path/to/test_file1.fits", "/path/to/test_file2.fits"]
                                    ) == ['test_file1.fits', 'test_file2.fits']
