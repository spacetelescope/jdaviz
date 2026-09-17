import numpy as np
from jdaviz.data.linelists import query_helpers
import pytest


def test_line_database_unique():
    '''
    Test that all line names in existing database are unique.
    '''
    database = query_helpers.load_db()
    assert len(database) == len(np.unique(database['line_name']))


def test_line_database_cache_reuses_table_instance():
    query_helpers.clear_db_cache()
    first = query_helpers.load_db()
    second = query_helpers.load_db()
    assert first is second


def test_get_lines():
    database = query_helpers.load_db()
    neon_lines = query_helpers.get_lines(database,
                                         wave_min=3000, wave_max=4000,
                                         element='Ne', science_case='galactic')
    # make sure it returns a table
    assert len(neon_lines) > 0
    # make sure [Ne V] 3426 has multiple tags including 'galactic'
    assert (neon_lines['science_case'][neon_lines['line_name'] == '[Ne V] 3426'][0] ==
            ['galactic', 'nebular', 'stellar'])
    # make sure [Ne V] 3346 has only one tag and it's 'galactic'
    assert (neon_lines['science_case'][neon_lines['line_name'] == '[Ne V] 3346'][0] ==
            'galactic')

    # you can only filter on one science case at a time
    with pytest.raises(AttributeError, match="'list' object has no attribute 'lower'"):
        query_helpers.get_lines(database, wave_min=3000, wave_max=4000,
                                element='Ne', science_case=['galactic', 'stellar'])
