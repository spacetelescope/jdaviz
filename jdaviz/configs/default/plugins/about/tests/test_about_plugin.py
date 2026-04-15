import pytest
from unittest.mock import patch

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


def test_about_basic(specviz_helper):
    """
    Test that the About plugin populates version info lazily.

    The PyPI check is deferred until the plugin is first opened,
    so before simulating an open we expect the default 'unknown'.
    """
    plg = specviz_helper.plugins['About']._obj

    assert plg.jdaviz_version == __version__

    # Before opening, pypi version has not been fetched yet.
    assert plg.jdaviz_pypi == 'unknown'
    assert plg._pypi_fetched is False

    # Simulate the plugin being opened (triggers the lazy fetch).
    # Mock the network call to avoid real HTTP requests in
    # non-remote tests.
    with patch(
        'jdaviz.configs.default.plugins.about.about'
        '.latest_version_from_pypi',
        return_value='99.0.0',
    ):
        plg.plugin_opened = True

    assert plg._pypi_fetched is True
    assert plg.jdaviz_pypi == '99.0.0'
    assert plg.not_is_latest is True
