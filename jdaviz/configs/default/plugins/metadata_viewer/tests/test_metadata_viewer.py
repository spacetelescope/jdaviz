import numpy as np
import pytest
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
    assert mv.dataset.labels == ['has_simple_meta[DATA]', 'has_nested_meta[DATA]', 'no_meta']

    mv.dataset_selected = 'has_simple_meta[DATA]'
    assert mv.has_metadata
    assert mv.metadata == [
        ('BAR', '10.0'), ('BOZO', 'None'), ('EXTNAME', 'SCI'),
        ('EXTVER', '1'), ('FOO', '')], mv.metadata

    mv.dataset_selected = 'has_nested_meta[DATA]'
    assert mv.has_metadata
    assert mv.metadata == [
        ('EXTNAME', 'ASDF'), ('REF.bar', '10.0'),
        ('REF.foo.1', ''), ('REF.foo.2.0', '1'), ('REF.foo.2.1', '2')], mv.metadata

    mv.dataset_selected = 'no_meta'
    assert not mv.has_metadata


def test_view_invalid(imviz_helper):
    mv = MetadataViewer(app=imviz_helper.app)
    assert mv.dataset.labels == []

    # Should not even happen but if it does, do not crash.
    with pytest.raises(ValueError):
        mv.dataset_selected = 'foo'
    assert mv.dataset_selected == ''
    assert not mv.has_metadata
    assert mv.metadata == []
