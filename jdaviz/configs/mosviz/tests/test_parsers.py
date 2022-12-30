from zipfile import ZipFile

import pytest
from astropy.utils.data import download_file

from jdaviz.utils import PRIHDR_KEY, COMMENTCARD_KEY


@pytest.mark.filterwarnings('ignore')
@pytest.mark.remote_data
@pytest.mark.parametrize('instrument_arg', ('nirspec', None))
def test_nirspec_parser(mosviz_helper, tmp_path, instrument_arg):
    '''
    Tests loading our default MosvizExample notebook data
    Also tests no instrument keyword fallback, and IntraRow linking
    '''

    test_data = 'https://stsci.box.com/shared/static/ovyxi5eund92yoadvv01mynwt8t5n7jv.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmp_path)

    level3_path = tmp_path / 'mosviz_nirspec_data_0.3' / 'level3'

    data_dir = level3_path

    if instrument_arg:
        mosviz_helper.load_data(directory=data_dir, instrument=instrument_arg)
    else:
        # When no instrument is provided, Mosviz now raises an error
        match = ('Ambiguous MOS Instrument: Only JWST NIRSpec, NIRCam, and NIRISS folder parsing'
                 ' are currently supported')
        with pytest.raises(ValueError, match=match):
            mosviz_helper.load_data(directory=data_dir)

        return

    assert len(mosviz_helper.app.data_collection) == 16

    # MOS Table meta should be empty:
    assert len(mosviz_helper.app.data_collection["MOS Table"].meta) == 0

    # Check that the data was loaded in the same order we expect.
    # MOS table always loads first, followed by 5 sets of Images, 1D, then 2D spectra
    #   which results in Images beginning at index 1, 1D at index 6, 2D at index 11
    assert mosviz_helper.app.data_collection[15].meta['SOURCEID'] == 2315
    for i in range(0, 5):
        assert mosviz_helper.app.data_collection[i+1].label == f"Image {i}"

        spec1d = mosviz_helper.app.data_collection[i+6]
        assert spec1d.label == f"1D Spectrum {i}"
        spec2d = mosviz_helper.app.data_collection[i+11]
        assert spec2d.label == f"2D Spectrum {i}"
        assert int(spec1d.meta['SOURCEID']) == int(spec2d.meta['SOURCEID'])
        assert int(spec1d.meta['mosviz_row']) == int(spec2d.meta['mosviz_row'])

    # Check for expected metadata values
    for data in mosviz_helper.app.data_collection:
        assert PRIHDR_KEY not in data.meta
        assert 'header' not in data.meta

        if 'IMAGE' in data.label:
            assert data.meta['WCSAXES'] == 2
        elif 'Spectrum' in data.label:
            assert data.meta['TARGNAME'] == 'FOO'

    # Test IntraRow linking:
    # Attempts to add the spectrum of another row into the current row's viewers
    # Currently, intrarow linking is disabled. Attemps to load another spectrum into
    # the current spectrum viewer should result in an error

    # Check to make sure our test case isn't from the same row to avoid false positive
    table = mosviz_helper.app.get_viewer('table-viewer')
    table.select_row(0)
    data_label = "1D Spectrum 4"
    assert mosviz_helper.app.data_collection[data_label].meta['mosviz_row'] != table.current_row

    with pytest.raises(NotImplementedError, match='Intra-row plotting not supported'):
        mosviz_helper.app.add_data_to_viewer(viewer_reference='spectrum-viewer',
                                             data_label=data_label)


@pytest.mark.filterwarnings('ignore')
@pytest.mark.remote_data
def test_nirspec_level2_parser(mosviz_helper, tmp_path):
    '''
    Tests loading our default MosvizExample notebook data
    Also tests no instrument keyword fallback, and IntraRow linking
    '''

    test_data = 'https://stsci.box.com/shared/static/mytqf082lpbfia7wlwjq6p1h5cggd9h6.zip'
    fn = download_file(test_data, cache=True, timeout=100)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmp_path)

    level3_path = tmp_path / 'jw02756001001_03103_00003_nrs1'

    data_dir = level3_path
    mosviz_helper.load_data(directory=data_dir, instrument='nirspec')

    assert len(mosviz_helper.app.data_collection) == 75


@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore', match="'(MJy/sr)^2' did not parse as fits unit")
def test_niriss_parser(mosviz_helper, tmp_path):
    '''
    Tests loading a NIRISS dataset
    This data set is a shortened version of the ERS program GLASS (Program 1324)
    provided by Camilla Pacifici. This is in-flight, "real" JWST data

    The spectra are jw01324001001_15101_00001_nis
    The direct image is jw01324-o001_t001_niriss_clear-f200w
    Please see JWST naming conventions for the above

    The dataset was uploaded to box by Duy Nguyen
    '''
    # TODO: Change back to smaller number (30?) when ITSD is convinced it is them and not us.
    #       Help desk ticket INC0183598, J. Quick.
    # Download data
    test_data = 'https://stsci.box.com/shared/static/cr14xijcg572dglacochctr1kblsr89a.zip'
    fn = download_file(test_data, cache=True, timeout=100)

    # Extract to a known, temporary folder
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmp_path)

    mosviz_helper.load_data(directory=tmp_path, instrument="niriss")
    assert len(mosviz_helper.app.data_collection) == 10

    # The image should be the first in the data collection
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == "Image jw01324-o001 F200W"
    assert PRIHDR_KEY not in dc_0.meta
    assert COMMENTCARD_KEY not in dc_0.meta
    assert dc_0.meta['bunit_data'] == 'MJy/sr'  # ASDF metadata

    # The MOS Table should be last in the data collection
    dc_tab = mosviz_helper.app.data_collection[-1]
    assert dc_tab.label == "MOS Table"
    assert len(dc_tab.meta) == 0

    # Test all the spectra exist
    for dispersion in ('R', 'C'):
        for sourceid in (243, 249):
            spec2d = mosviz_helper.app.data_collection[
                f"F200W Source {sourceid} spec2d {dispersion}"]
            spec1d = mosviz_helper.app.data_collection[
                f"F200W Source {sourceid} spec1d {dispersion}"]

            # Header should be imported from the spec2d files
            assert PRIHDR_KEY in spec2d.meta
            assert COMMENTCARD_KEY in spec2d.meta

            # Header should NOT be imported from spec1d files:
            assert PRIHDR_KEY not in spec1d.meta
            assert COMMENTCARD_KEY in spec1d.meta
            assert 'header' not in spec1d.meta

            # Other Metadata Checks:
            assert spec1d.meta['FILTER'] == f'GR150{dispersion}'
            assert int(spec1d.meta['mosviz_row']) == int(spec2d.meta['mosviz_row'])

            for spec in (spec1d, spec2d):
                assert spec.meta['SOURCEID'] == sourceid


@pytest.mark.remote_data
@pytest.mark.filterwarnings('ignore', match="'(MJy/sr)^2' did not parse as fits unit")
def test_nircam_parser(mosviz_helper, tmp_path):
    '''
    Tests loading a NIRCam dataset
    '''

    # Download data
    test_data = 'https://stsci.box.com/shared/static/itk7pav073nubwn58pig002m9796qzpw.zip'
    fn = download_file(test_data, cache=True, timeout=100)

    # Extract to a known, temporary folder
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmp_path)

    mosviz_helper.load_data(directory=tmp_path / "trimmed_nircam_data", instrument="nircam")

    # The MOS Table should be last in the data collection
    dc_tab = mosviz_helper.app.data_collection[-1]
    assert dc_tab.label == "MOS Table"
    assert len(dc_tab.meta) == 0

    # Check that the correct amount of spectra got loaded in the correct order
    assert len(mosviz_helper.app.data_collection) == 31
    assert mosviz_helper.app.data_collection['MOS Table']['Identifier'][0] == 1112
    assert mosviz_helper.app.data_collection[0].label == 'F322W2 Source 1112 spec2d R'
    assert mosviz_helper.app.data_collection[15].label == 'F322W2 Source 1112 spec1d R'


@pytest.mark.remote_data
def test_missing_srctype(mosviz_helper, tmp_path):
    '''
    Tests that data missing the SRCTYPE keyword raises a warning to the user.

    SRCTYPE is required for Mosviz. We do not want to rely on the JWST x1d parser's
    default behavior of overwriting with "POINT" if it doesn't exist, as all NIRISS data
    should have this populated; missing SRCTYPE indicates something went wrong.

    This dataset was our original simulated NIRISS dataset that is missing SRCTYPE.

    NOTE: Under some conditions, a warning is raised when TemporaryDirectory attempts to
    clean itself up. Most likely a race condition between TempDir and pytest
    '''

    # Download data
    test_data = 'https://stsci.box.com/shared/static/l2azhcqd3tvzhybdlpx2j2qlutkaro3z.zip'
    fn = download_file(test_data, cache=True, timeout=30)

    # Extract to a known, temporary folder
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmp_path)

    with pytest.raises(KeyError, match=r".*The SRCTYPE keyword.*is not populated.*"):
        mosviz_helper.load_data(directory=(tmp_path / 'NIRISS_for_parser_p0171'),
                                instrument="niriss")
