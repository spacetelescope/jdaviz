import numpy as np
from astropy.nddata import NDData

from jdaviz.configs.default.plugins.metadata_viewer.metadata_viewer import MetadataViewer


def test_view_dict(imviz_helper):
    mv = MetadataViewer(app=imviz_helper.app)
    ndd_1 = NDData(np.zeros((2, 2)), meta={
        'EXTNAME': 'SCI', 'EXTVER': 1, 'BAR': 10.0,
        'FOO': '', 'COMMENT': 'a test', 'BOZO': None})
    ndd_2 = NDData(np.ones((2, 2)), meta={
        'EXTNAME': 'ASDF', 'REF': {'bar': 10.0, 'foo': {'1': '', '2': [1, 2]}}})
    arr = np.zeros((2, 2))
    imviz_helper.load_data(ndd_1, data_label='has_simple_meta')
    imviz_helper.load_data(ndd_2, data_label='has_nested_meta')
    imviz_helper.load_data(arr, data_label='no_meta')
    assert mv.dc_items == ['has_simple_meta[DATA]', 'has_nested_meta[DATA]', 'no_meta']

    mv.selected_data = 'has_simple_meta[DATA]'
    assert mv.has_metadata
    assert mv.metadata == [
        ('BAR', '10.0'), ('BOZO', 'None'), ('EXTNAME', 'SCI'),
        ('EXTVER', '1'), ('FOO', '')], mv.metadata

    mv.selected_data = 'has_nested_meta[DATA]'
    assert mv.has_metadata
    assert mv.metadata == [
        ('EXTNAME', 'ASDF'), ('REF.bar', '10.0'),
        ('REF.foo.1', ''), ('REF.foo.2.0', '1'), ('REF.foo.2.1', '2')], mv.metadata

    mv.selected_data = 'no_meta'
    assert not mv.has_metadata
    assert mv.metadata == []


def test_view_invalid(imviz_helper):
    mv = MetadataViewer(app=imviz_helper.app)
    assert mv.dc_items == []

    # Should not even happen but if it does, do not crash.
    mv.selected_data = 'foo'
    assert not mv.has_metadata
    assert mv.metadata == []
