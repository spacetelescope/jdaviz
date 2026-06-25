import pytest


def test_user_api(deconfigged_helper):
    plugin = deconfigged_helper.plugins['Compass']

    with pytest.raises(AttributeError):
        plugin.data_label = 'cannot set readonly'
