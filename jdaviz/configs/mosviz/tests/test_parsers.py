from zipfile import ZipFile

import pytest
from numpy.testing import assert_allclose
from astropy.utils.data import download_file

from jdaviz.utils import PRIHDR_KEY, COMMENTCARD_KEY


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
    # MOS table always loads first, followed by 5 sets of 1D Spectra, 2D Spectra, then Images
    #   which results in 1D beginning at index 1, 2D at index 6, and Images at index 11
    assert mosviz_helper.app.data_collection[5].meta['SOURCEID'] == 2315
    for i in range(0, 5):
        # Check 1D spectra
        spec1d = mosviz_helper.app.data_collection[i+1]
        assert spec1d.label == f"1D Spectrum {i}"
        # Check 2D spectra
        spec2d = mosviz_helper.app.data_collection[i+6]
        assert spec2d.label == f"2D Spectrum {i}"
        assert int(spec1d.meta['SOURCEID']) == int(spec2d.meta['SOURCEID'])
        assert int(spec1d.meta['mosviz_row']) == int(spec2d.meta['mosviz_row'])
        # Check images
        assert mosviz_helper.app.data_collection[i+11].label == f"Image {i}"

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

    # The MOS Table should be first in the data collection
    dc_tab = mosviz_helper.app.data_collection[0]
    assert dc_tab.label == "MOS Table"
    assert len(dc_tab.meta) == 0

    # The image should be the first "real data" in the data collection
    dc_1 = mosviz_helper.app.data_collection[1]
    assert dc_1.label == "Image jw01324-o001 F200W"
    assert PRIHDR_KEY not in dc_1.meta
    assert COMMENTCARD_KEY not in dc_1.meta
    assert dc_1.meta['bunit_data'] == 'MJy/sr'  # ASDF metadata

    # We should be centered on the coordinates of the first data point
    imview = mosviz_helper.app.get_viewer(mosviz_helper._default_image_viewer_reference_name)
    x_pixcenter = (imview.state.x_max + imview.state.x_min)/2.0
    y_pixcenter = (imview.state.y_max + imview.state.y_min)/2.0
    viewer_center_coord = imview.layers[0].layer.coords.pixel_to_world(x_pixcenter, y_pixcenter)
    assert_allclose(viewer_center_coord.ra.deg, dc_tab["R.A."][0])
    assert_allclose(viewer_center_coord.dec.deg, dc_tab["Dec."][0])

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

    # The MOS Table should be first in the data collection
    dc_tab = mosviz_helper.app.data_collection[0]
    assert dc_tab.label == "MOS Table"
    assert len(dc_tab.meta) == 0

    # Check that the correct amount of spectra got loaded in the correct order
    assert len(mosviz_helper.app.data_collection) == 31
    assert mosviz_helper.app.data_collection['MOS Table']['Identifier'][0] == 1112
    assert mosviz_helper.app.data_collection[1].label == 'F322W2 Source 1112 spec2d R'
    assert mosviz_helper.app.data_collection[16].label == 'F322W2 Source 1112 spec1d R'


@pytest.mark.remote_data
def test_missing_srctype(mosviz_helper, tmp_path):
    '''
    Tests that data missing the SRCTYPE keyword raises a warning to the user.

    SRCTYPE is required for Mosviz. We do not want to rely on the JWST x1d parser's
    default behavior of overwriting with "POINT" if it doesn't exist, as all NIRISS data
    should have this populated; missing SRCTYPE indicates something went wrong.

    This dataset was our original simulated NIRISS dataset that is missing SRCTYPE.

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
