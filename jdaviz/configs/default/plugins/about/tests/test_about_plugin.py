import pytest

from jdaviz import __version__
from jdaviz.configs.default.plugins.about.about import latest_version_from_pypi


@pytest.mark.remote_data
def test_get_latest_version_from_pypi():
    # Since the latest version will change over time,
    # we can only check that something is returned but not what exactly.

    v = latest_version_from_pypi("jdaviz")
    assert isinstance(v, str)

    v = latest_version_from_pypi("fakespacetelescopepackage")
    assert v is None


# NOTE: The PyPI version check is cached per-process, so only the first
# Application init in a given process triggers a network request.
def test_about_basic(specviz_helper):
    plg = specviz_helper.plugins["About"]._obj

    assert plg.jdaviz_version == __version__
    assert isinstance(plg.jdaviz_pypi, str)
    # not_is_latest can be non-deterministic because user can be running
    # this test from an older version going forward, so we skip checking it.
