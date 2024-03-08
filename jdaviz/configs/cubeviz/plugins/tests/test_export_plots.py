import os

import pytest

from jdaviz.configs.default.plugins.export.export import HAS_OPENCV


# TODO: Remove skip when https://github.com/bqplot/bqplot/pull/1397/files#r726500097 is resolved.
@pytest.mark.skip(reason="Cannot test due to async JS callback")
# @pytest.mark.skipif(not HAS_OPENCV, reason="opencv-python is not installed")
def test_export_movie(cubeviz_helper, spectrum1d_cube, tmp_path):
    orig_path = os.getcwd()
    os.chdir(tmp_path)
    try:
        cubeviz_helper.load_data(spectrum1d_cube, data_label="test")
        plugin = cubeviz_helper.plugins["Export"]
        assert plugin._obj.i_start == 0
        assert plugin._obj.i_end == 1

        plugin.viewer_format = 'mp4'
        plugin._obj.export()
        assert os.path.isfile("mymovie.mp4"), tmp_path
    finally:
        os.chdir(orig_path)


@pytest.mark.skipif(HAS_OPENCV, reason="opencv-python is installed")
def test_no_opencv(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label="test")
    plugin = cubeviz_helper.plugins["Export"]
    assert 'mp4' in plugin.viewer_format.choices
    assert not plugin._obj.movie_enabled
    plugin.viewer_format = 'mp4'
    with pytest.raises(ImportError, match="Please install opencv-python"):
        plugin.export()


@pytest.mark.skipif(not HAS_OPENCV, reason="opencv-python is not installed")
def test_export_movie_not_cubeviz(imviz_helper):
    plugin = imviz_helper.plugins["Export"]
    assert 'mp4' not in plugin.viewer_format.choices


@pytest.mark.skipif(not HAS_OPENCV, reason="opencv-python is not installed")
def test_export_movie_cubeviz_exceptions(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label="test")
    cubeviz_helper.default_viewer._obj.shape = (100, 100)
    cubeviz_helper.app.get_viewer("uncert-viewer").shape = (100, 100)
    plugin = cubeviz_helper.plugins["Export"]
    assert plugin._obj.i_start == 0
    assert plugin._obj.i_end == 1

    plugin.viewer_format = 'mp4'
    plugin._obj.i_end = 0
    with pytest.raises(ValueError, match="No frames to write"):
        plugin.export()

    plugin._obj.i_end = 1
    plugin._obj.movie_fps = 0
    with pytest.raises(ValueError, match="Invalid frame rate"):
        plugin.export()

    plugin._obj.movie_fps = 5
    plugin.filename = "fake_path/mymovie.mp4"
    with pytest.raises(ValueError, match="Invalid path"):
        plugin.export()

    plugin.filename = ""
    plugin.viewer = 'uncert-viewer'
    with pytest.raises(ValueError, match="Invalid filename"):
        plugin.export()


@pytest.mark.skipif(not HAS_OPENCV, reason="opencv-python is not installed")
def test_export_movie_cubeviz_empty(cubeviz_helper):
    plugin = cubeviz_helper.plugins["Export"]
    assert plugin._obj.i_start == 0
    assert plugin._obj.i_end == 0

    plugin.viewer_format = 'mp4'
    with pytest.raises(ValueError, match="Selected viewer has no display shape"):
        plugin.export()


def test_export_plot_exceptions(cubeviz_helper):
    plugin = cubeviz_helper.plugins["Export"]

    plugin.filename = "/fake/path/image.png"
    with pytest.raises(ValueError, match="Invalid path"):
        plugin.export()
