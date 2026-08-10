import numpy as np
from jdaviz.data.linelists import query_helpers


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
