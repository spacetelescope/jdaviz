import numpy as np
import pytest

from jdaviz.core.table_row_sync import (PluginTableRowSync,
                                        PluginTableRowSyncGroup,
                                        decode_row_sync_recipe,
                                        encode_row_sync_recipe)


def test_scalar_and_group_descriptor_validation():
    dataset = PluginTableRowSync('dataset', 'dataset_selected',
                                 value_kind='data_label',
                                 manual_values=('From Plugin',))
    group = PluginTableRowSyncGroup('recipe', (dataset,), label='Extraction')

    assert group.members == (dataset,)
    with pytest.raises(ValueError, match='unique'):
        PluginTableRowSyncGroup('recipe', (dataset, dataset))
    with pytest.raises(ValueError, match='only valid for data_label'):
        PluginTableRowSync('mode', 'mode_selected', manual_values=('Default',))

    selected = PluginTableRowSync('pa', 'pa', selectors=(('overlay', 'default'),))
    assert selected.rename_selector('overlay', 'default', 'renamed').selectors == (
        ('overlay', 'renamed'),)


def test_recipe_json_is_canonical_and_normalizes_numpy_scalars():
    first = encode_row_sync_recipe({'width': np.int64(3), 'enabled': np.bool_(True)})
    second = encode_row_sync_recipe({'enabled': True, 'width': 3})

    assert first == second
    assert decode_row_sync_recipe(first) == {'enabled': True, 'width': 3}
    assert decode_row_sync_recipe('{"enabled":true,"width":3}') == {'enabled': True, 'width': 3}


@pytest.mark.parametrize('value', [np.nan, np.inf, object()])
def test_recipe_json_rejects_unsupported_values(value):
    error = ValueError if isinstance(value, float) else TypeError
    with pytest.raises(error):
        encode_row_sync_recipe({'value': value})


def test_recipe_json_rejects_invalid_or_unknown_payloads():
    with pytest.raises(ValueError, match='invalid'):
        decode_row_sync_recipe('{')
    assert decode_row_sync_recipe('{}') == {}
    assert decode_row_sync_recipe('{"enabled":true}') == {'enabled': True}
