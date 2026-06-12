import csv

from jdaviz.core.loaders.resolvers.file.file import FileResolver


def test_file_resolver_is_valid(deconfigged_helper, tmp_path):
    """Test _check_is_valid for FileResolver: success and failure cases."""
    resolver = FileResolver(app=deconfigged_helper._app)

    # Success: existing file
    real_file = tmp_path / 'real.fits'
    real_file.write_text('data')
    resolver.filepath = str(real_file)
    assert resolver._check_is_valid() == ''

    # Failure: nonexistent file path
    resolver.filepath = str(tmp_path / 'nonexistent.fits')
    assert resolver._check_is_valid() == 'Filepath does not exist.'

    # Failure: directory instead of file
    resolver.filepath = str(tmp_path)
    assert resolver._check_is_valid() == 'Filepath is not a file.'


def test_mast_export_csv_treat_table_as_query(deconfigged_helper, tmp_path):
    """
    Test that a Missions-MAST-export CSV (Dataset + Filename columns) loaded via
    the file resolver correctly sets parsed_input_is_query=True, making the
    treat_table_as_query toggle visible, and populates the file table.

    The MAST export format has both a 'Dataset' column (observation identifier)
    and a 'Filename' column (product filename). 'Filename' maps to 'location'
    in the file table, so file_table_populated should be True.
    """
    # Write a CSV that mimics the Missions MAST export format
    csv_file = tmp_path / 'mast_export.csv'
    fieldnames = ['Dataset', 'Filename', 'Product Level', 'Suffix',
                  'Instrument', 'Filter / Grating']
    rows = [
        {
            'Dataset': 'jw01860-c1001_t004_miri',
            'Filename': 'jw01860-c1001_t004_miri_ch1-long_s3d.fits',
            'Product Level': '3', 'Suffix': '_s3d',
            'Instrument': 'MIRI', 'Filter / Grating': 'MIRIFU_CHANNEL1A',
        },
        {
            'Dataset': 'jw01860-c1001_t004_miri',
            'Filename': 'jw01860-c1001_t004_miri_ch1-long_x1d.fits',
            'Product Level': '3', 'Suffix': '_x1d',
            'Instrument': 'MIRI', 'Filter / Grating': 'MIRIFU_CHANNEL1A',
        },
    ]
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    resolver = FileResolver(app=deconfigged_helper._app)
    resolver.filepath = str(csv_file)

    # The treat_table_as_query toggle must be visible
    assert resolver.parsed_input_is_query is True
    # 'Filename' maps to 'location' → file table is populated, not observation table
    assert resolver.file_table_populated is True
    assert resolver.observation_table_populated is False

    # Toggling off must keep parsed_input_is_query True so the switch stays visible
    resolver.treat_table_as_query = False
    assert resolver.parsed_input_is_query is True
    assert resolver.file_table_populated is False
    assert resolver.observation_table_populated is False

    # Toggling back on must re-populate the file table
    resolver.treat_table_as_query = True
    assert resolver.parsed_input_is_query is True
    assert resolver.file_table_populated is True


def test_mast_search_results_csv_treat_table_as_query(deconfigged_helper, tmp_path):
    """
    Test that a MAST portal search-results CSV (obs_id + dataURL + s_region columns)
    loaded via the file resolver correctly sets parsed_input_is_query=True and
    populates the observation table (obs_id → Dataset, with s_region present).

    This format is exported by the MAST search portal and has:
    - Comment lines at the top starting with '#'
    - obs_id as the observation identifier (should map to 'Dataset')
    - dataURL as the data product URI (should map to 'location')
    - s_region containing WCS footprint polygons
    """
    csv_file = tmp_path / 'mast_search_results.csv'
    # Mimic the exact header/comment structure of a MAST portal export
    lines = [
        '#The following lines beginning with # are comments.',
        '#@string, string, string, string, string',
        '#Observation Type, Observation ID, RA, Dec, Data URL, s_region',
        'intentType,obs_id,s_ra,s_dec,dataURL,s_region',
        'science,jw01309-o015_t006-s000000023_nirspec_f290lp-g395h,166.59,-77.40,'
        'mast:JWST/product/jw01309-o015_s2d.fits,'
        'POLYGON 166.59 -77.40 166.60 -77.40 166.60 -77.41 166.59 -77.41',
        'science,jw01309-o022_t008-s000000024_nirspec_f290lp-g395h,166.61,-77.39,'
        'mast:JWST/product/jw01309-o022_s2d.fits,'
        'POLYGON 166.61 -77.39 166.62 -77.39 166.62 -77.40 166.61 -77.40',
    ]
    csv_file.write_text('\n'.join(lines))

    resolver = FileResolver(app=deconfigged_helper._app)
    resolver.filepath = str(csv_file)

    # The treat_table_as_query toggle must be visible
    assert resolver.parsed_input_is_query is True
    # obs_id → Dataset mapping → observation table is populated
    assert resolver.observation_table_populated is True
    assert resolver.file_table_populated is False
    # s_region must be present so footprints can be drawn
    assert 's_region' in resolver.observation_table.headers_avail

    # Toggling off keeps the switch visible
    resolver.treat_table_as_query = False
    assert resolver.parsed_input_is_query is True
    assert resolver.observation_table_populated is False

    # Toggling back on re-populates
    resolver.treat_table_as_query = True
    assert resolver.parsed_input_is_query is True
    assert resolver.observation_table_populated is True
