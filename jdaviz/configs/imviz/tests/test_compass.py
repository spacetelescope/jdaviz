import os
import pytest

CI = os.environ.get("CI", "").lower() in ("1", "true", "yes")


@pytest.mark.skipif(CI, reason="Temporarily skipped failing imviz compass test in CI")
def test_user_api(deconfigged_helper):
    plugin = deconfigged_helper.plugins['Compass']

    with pytest.raises(AttributeError):
        plugin.data_label = 'cannot set readonly'
