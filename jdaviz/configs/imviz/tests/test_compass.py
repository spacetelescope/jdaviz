import pytest


def test_user_api(imviz_helper):
    plugin = imviz_helper.plugins['Compass']

    with pytest.raises(AttributeError):
        plugin.data_label = 'cannot set readonly'
