# Licensed under a 3-clause BSD style license - see LICENSE.rst

from copy import deepcopy
from unittest.mock import Mock

import pytest
import yaml

from jdaviz.app import PrivateApplication
from jdaviz.core.config import get_configuration
from jdaviz.core.viewer_layout import ViewerLayoutError, iter_viewer_ids, remove_viewer


def test_application_resolves_config_into_canonical_state():
    app = PrivateApplication(configuration=get_configuration('cubeviz'))

    viewer_ids = [item['id'] for item in app.state.viewer_items]
    assert viewer_ids == ['cubeviz-0', 'cubeviz-1', 'cubeviz-2']
    assert iter_viewer_ids(app.state.viewer_layout) == tuple(viewer_ids)
    assert app.state.viewer_layout['root']['type'] == 'column'
    assert all(item['closable'] is False for item in app.state.viewer_items)


def test_application_accepts_existing_configuration_without_mutation():
    config = deepcopy(get_configuration('imviz'))

    original = deepcopy(config)
    app = PrivateApplication(configuration=config)

    assert config == original
    assert app.get_configuration() == original
    assert iter_viewer_ids(app.state.viewer_layout) == ('imviz-0',)
    assert app.state.viewer_items[0]['closable'] is False


def test_dynamic_viewer_add_remove_updates_one_authoritative_state(imviz_helper):
    app = imviz_helper._app
    added = imviz_helper.create_image_viewer(viewer_name='added')

    assert added._reference_id == 'added'
    assert iter_viewer_ids(app.state.viewer_layout) == ('imviz-0', 'added')
    assert [child['weight'] for child in app.state.viewer_layout['root']['children']] == [0.5, 0.5]
    assert [item['id'] for item in app.state.viewer_items] == ['imviz-0', 'added']

    app.state.focus_viewer = 'added'
    imviz_helper.destroy_viewer('added')

    assert iter_viewer_ids(app.state.viewer_layout) == ('imviz-0',)
    assert [item['id'] for item in app.state.viewer_items] == ['imviz-0']
    assert app.state.focus_viewer == ''


def test_renderer_close_event_updates_layout_and_registry_together(imviz_helper):
    app = imviz_helper._app
    imviz_helper.create_image_viewer(viewer_name='added')
    rendered_layout = remove_viewer(app.state.viewer_layout, 'added')

    app.vue_close_viewer({
        'viewerId': 'added',
        'layout': rendered_layout,
    })

    assert iter_viewer_ids(app.state.viewer_layout) == ('imviz-0',)
    assert [item['id'] for item in app.state.viewer_items] == ['imviz-0']


def test_browser_close_requires_a_valid_post_close_layout(imviz_helper):
    app = imviz_helper._app
    imviz_helper.create_image_viewer(viewer_name='added')
    accepted = deepcopy(app.state.viewer_layout)
    with pytest.raises(ViewerLayoutError, match='must be an object'):
        app.vue_close_viewer({'viewerId': 'added'})
    assert app.viewer_layout_reset == 1
    assert app.state.viewer_layout == accepted
    assert set(app._viewer_store) == {'imviz-0', 'added'}


def test_user_layout_update_is_validated_against_live_registry(imviz_helper):
    app = imviz_helper._app
    imviz_helper.create_image_viewer(viewer_name='added')
    moved = deepcopy(app.state.viewer_layout)
    moved['root']['children'][0]['weight'] = 1
    moved['root']['children'][1]['weight'] = 3

    app.vue_set_viewer_layout(moved)

    assert [child['weight'] for child in app.state.viewer_layout['root']['children']] == [
        0.25, 0.75
    ]

    invalid = remove_viewer(app.state.viewer_layout, 'added')
    accepted = deepcopy(app.state.viewer_layout)
    previous_reset = app.viewer_layout_reset
    with pytest.raises(ViewerLayoutError, match='missing viewer IDs'):
        app.vue_set_viewer_layout(invalid)
    assert app.state.viewer_layout == accepted
    assert app.viewer_layout_reset == previous_reset + 1


def test_protected_ui_close_resets_preview_but_programmatic_removal_is_allowed(imviz_helper):
    app = imviz_helper._app
    accepted = deepcopy(app.state.viewer_layout)
    viewer = app._viewer_store['imviz-0']
    with pytest.raises(ViewerLayoutError, match='cannot be closed'):
        app.vue_close_viewer({
            'viewerId': 'imviz-0', 'layout': {'version': 1, 'root': None},
        })
    assert app.viewer_layout_reset == 1
    assert app.state.viewer_layout == accepted
    assert app._viewer_store['imviz-0'] is viewer
    app.vue_destroy_viewer_item('imviz-0')
    assert app.state.viewer_layout == {'version': 1, 'root': None}
    assert app.state.viewer_items == []


def test_stale_close_cannot_remove_another_viewer(imviz_helper):
    app = imviz_helper._app
    imviz_helper.create_image_viewer(viewer_name='added')
    accepted = deepcopy(app.state.viewer_layout)
    with pytest.raises(ViewerLayoutError, match='missing viewer IDs'):
        app.vue_close_viewer({
            'viewerId': 'added', 'layout': {'version': 1, 'root': None},
        })
    assert app.viewer_layout_reset == 1
    assert app.state.viewer_layout == accepted
    assert set(app._viewer_store) == {'imviz-0', 'added'}
    app.vue_destroy_viewer_item('added')
    app.vue_close_viewer({'viewerId': 'added', 'layout': accepted})
    assert app.viewer_layout_reset == 2
    assert iter_viewer_ids(app.state.viewer_layout) == ('imviz-0',)


@pytest.mark.parametrize('configuration', [
    'default', 'deconfigged', 'imviz', 'specviz', 'specviz2d', 'cubeviz', 'mosviz', 'rampviz',
])
def test_bundled_configuration_instantiates_layout(configuration):
    config = get_configuration(configuration)
    app = PrivateApplication(configuration=config)
    ids = [item['id'] for item in app.state.viewer_items]
    assert set(iter_viewer_ids(app.state.viewer_layout)) == set(ids)

    def configured_viewers(items):
        return [view for item in items
                for view in [*item.get('viewers', []),
                             *configured_viewers(item.get('children', []))]]

    specs = configured_viewers(config.get('viewer_area') or [])
    assert ids == [f'{configuration}-{index}' for index in range(len(specs))]
    assert [item['reference'] for item in app.state.viewer_items] == [
        spec.get('reference') or spec.get('name') or vid for spec, vid in zip(specs, ids)]


def test_external_yaml_configuration(tmp_path):
    config = get_configuration('imviz')
    path = tmp_path / 'custom.yaml'
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    app = PrivateApplication(configuration=str(path))
    assert iter_viewer_ids(app.state.viewer_layout) == ('imviz-0',)


@pytest.mark.parametrize('container, expected_type', [
    ('row', 'row'), ('col', 'column'), ('stack', 'stack'),
])
def test_existing_inline_viewers_keep_split_or_tab_semantics(container, expected_type):
    config = get_configuration('default')
    config['viewer_area'] = [{'container': container, 'viewers': [
        {'plot': 'spectrum-1d-viewer', 'reference': 'first'},
        {'plot': 'spectrum-1d-viewer', 'reference': 'second'},
    ]}]
    original = deepcopy(config)
    app = PrivateApplication(configuration=config)
    root = app.state.viewer_layout['root']
    assert root['type'] == expected_type
    ids = [item['id'] for item in app.state.viewer_items]
    assert iter_viewer_ids(app.state.viewer_layout) == tuple(ids)
    if container == 'stack':
        assert root['viewers'] == ids
    else:
        assert [child['viewers'] for child in root['children']] == [[vid] for vid in ids]
    assert config == original


@pytest.mark.parametrize('container', ['row', 'col', 'stack'])
def test_mixed_containers_preserve_creation_and_display_order(container):
    config = get_configuration('default')
    config['viewer_area'] = [
        {'container': container,
         'viewers': [{'plot': 'spectrum-1d-viewer', 'reference': 'parent'}],
         'children': [{'container': 'stack', 'viewers': [
             {'plot': 'spectrum-1d-viewer', 'reference': 'child'}]}]},
        {'container': 'stack', 'viewers': [
            {'plot': 'spectrum-1d-viewer', 'reference': 'sibling'}]},
    ]
    app = PrivateApplication(configuration=config)
    items = app.state.viewer_items
    assert [item['reference'] for item in items] == ['parent', 'child', 'sibling']
    assert iter_viewer_ids(app.state.viewer_layout) == (
        items[1]['id'], items[0]['id'], items[2]['id'])
    root = app.state.viewer_layout['root']
    assert root['type'] == 'row'
    assert root['children'][0]['type'] == ('row' if container == 'row' else 'column')


class _RecordingComm:
    """Stand in for a live comm so that ipywidgets sends state updates in tests."""

    kernel = True

    def __init__(self, comm_id, sent_states):
        self.comm_id = comm_id
        self._sent_states = sent_states

    def on_msg(self, callback):
        pass

    def send(self, data=None, buffers=None):
        self._sent_states.append(data.get('state', {}))


@pytest.mark.parametrize('update_id', [False, True])
def test_existing_rename_api_preserves_viewer_and_widget(imviz_helper, monkeypatch, update_id):
    app = imviz_helper._app
    imviz_helper.create_image_viewer(viewer_name='added')
    viewer = app.get_viewer_by_id('added')
    widget = app._viewer_item_by_id('added')['widget']
    app.state.focus_viewer = 'added'
    app.state.viewer_layout = {'version': 1, 'root': {
        'type': 'stack', 'viewers': ['imviz-0', 'added'], 'activeViewerId': 'added'},
        'maximizedViewerId': 'added'}
    # Capture the state updates sent to the frontend at the comm level, where
    # batched trait changes arrive as one message. The widget needs a comm that
    # looks live, since ipywidgets drops messages without a kernel.
    sent_states = []
    monkeypatch.setattr(app, 'comm', _RecordingComm(app.model_id, sent_states))

    app._update_viewer_reference_name('added', 'renamed', update_id=update_id)

    vid = 'renamed' if update_id else 'added'
    # The frontend must never receive a layout naming an ID that its viewer
    # items do not have, so a renamed ID arrives together with the renamed items.
    layout_updates = [state for state in sent_states if 'state_viewer_layout' in state]
    assert len(layout_updates) == (1 if update_id else 0)
    for state in layout_updates:
        assert 'state_viewer_items' in state, 'layout sent without the renamed viewer items'
        assert set(iter_viewer_ids(state['state_viewer_layout'])) == {
            item['id'] for item in state['state_viewer_items']}
    assert app.get_viewer_by_id(vid) is viewer
    assert app._viewer_item_by_id(vid)['widget'] == widget
    assert app._viewer_item_by_reference('renamed')['id'] == vid
    assert app.state.focus_viewer == 'renamed'
    assert iter_viewer_ids(app.state.viewer_layout) == ('imviz-0', vid)
    assert app.state.viewer_layout['root']['activeViewerId'] == vid
    assert app.state.viewer_layout['maximizedViewerId'] == vid

    app.vue_destroy_viewer_item(cid=vid)
    assert iter_viewer_ids(app.state.viewer_layout) == ('imviz-0',)


@pytest.mark.parametrize('viewer_id', ['imviz-0', '', 12])
def test_invalid_new_viewer_id_does_not_mutate_registry(imviz_helper, monkeypatch, viewer_id):
    app = imviz_helper._app
    original = app._viewer_store.copy()
    layout = deepcopy(app.state.viewer_layout)
    create_viewer = Mock(wraps=app._application_handler.new_data_viewer)
    monkeypatch.setattr(app._application_handler, 'new_data_viewer', create_viewer)
    with pytest.raises(ViewerLayoutError):
        imviz_helper.create_image_viewer(viewer_name=viewer_id)
    create_viewer.assert_not_called()
    assert app._viewer_store == original
    assert [item['id'] for item in app.state.viewer_items] == ['imviz-0']
    assert app.state.viewer_layout == layout
