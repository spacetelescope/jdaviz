import numpy as np
from jdaviz.data.linelists import query_helpers, ingest


def test_line_database_unique():
    '''
    Test that all line names in existing database are unique.
    '''
    database = query_helpers.load_db()
    assert len(database) == len(np.unique(database['line_name']))


def test_line_database_ingest():
    '''
    Test that all lines in a newly created database are unique.
    '''
    new_database = ingest.build_database()
    assert len(new_database) == len(np.unique(new_database['line_name']))
