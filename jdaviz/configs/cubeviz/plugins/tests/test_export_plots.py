import os

import pytest

from jdaviz.configs.default.plugins.export_plot.export_plot import HAS_OPENCV


# TODO: Remove skip when https://github.com/bqplot/bqplot/pull/1397/files#r726500097 is resolved.
@pytest.mark.skip(reason="Cannot test due to async JS callback")
# @pytest.mark.skipif(not HAS_OPENCV, reason="opencv-python is not installed")
def test_export_movie(cubeviz_helper, spectrum1d_cube, tmp_path):
    orig_path = os.getcwd()
    os.chdir(tmp_path)
    try:
        cubeviz_helper.load_data(spectrum1d_cube, data_label="test")
        plugin = cubeviz_helper.plugins["Export Plot"]
        assert plugin.i_start == 0
        assert plugin.i_end == 1
        assert plugin.movie_filename == "mymovie.mp4"

        plugin._obj.vue_save_movie("mp4")
        assert os.path.isfile("mymovie.mp4"), tmp_path
    finally:
        os.chdir(orig_path)


@pytest.mark.skipif(HAS_OPENCV, reason="opencv-python is installed")
def test_no_opencv(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label="test")
    plugin = cubeviz_helper.plugins["Export Plot"]
    assert plugin._obj.movie_msg != ""
    with pytest.raises(ImportError, match="Please install opencv-python"):
        plugin.save_movie()


@pytest.mark.skipif(not HAS_OPENCV, reason="opencv-python is not installed")
def test_export_movie_not_cubeviz(imviz_helper):
    plugin = imviz_helper.plugins["Export Plot"]

    with pytest.raises(NotImplementedError, match="save_movie is not available for config"):
        plugin._obj.save_movie()

    # Also not available via plugin public API.
    with pytest.raises(AttributeError):
        plugin.save_movie()


@pytest.mark.skipif(not HAS_OPENCV, reason="opencv-python is not installed")
def test_export_movie_cubeviz_exceptions(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label="test")
    cubeviz_helper.default_viewer.shape = (100, 100)
    cubeviz_helper.app.get_viewer("uncert-viewer").shape = (100, 100)
    plugin = cubeviz_helper.plugins["Export Plot"]
    assert plugin._obj.movie_msg == ""
    assert plugin.i_start == 0
    assert plugin.i_end == 1
    assert plugin.movie_filename == "mymovie.mp4"

    with pytest.raises(NotImplementedError, match="filetype"):
        plugin.save_movie(filetype="gif")

    with pytest.raises(NotImplementedError, match="filetype"):
        plugin.save_movie(filename="mymovie.gif", filetype=None)

    with pytest.raises(ValueError, match="No frames to write"):
        plugin.save_movie(i_start=0, i_end=0)

    with pytest.raises(ValueError, match="Invalid frame rate"):
        plugin.save_movie(fps=0)

    plugin.movie_filename = "fake_path/mymovie.mp4"
    with pytest.raises(ValueError, match="Invalid path"):
        plugin.save_movie()

    plugin.movie_filename = "mymovie.mp4"
    plugin.viewer = 'spectrum-viewer'
    with pytest.raises(TypeError, match=r"Movie for.*is not supported"):
        plugin.save_movie()

    plugin.movie_filename = ""
    plugin.viewer = 'uncert-viewer'
    with pytest.raises(ValueError, match="Invalid filename"):
        plugin.save_movie()


@pytest.mark.skipif(not HAS_OPENCV, reason="opencv-python is not installed")
def test_export_movie_cubeviz_empty(cubeviz_helper):
    plugin = cubeviz_helper.plugins["Export Plot"]
    assert plugin.i_start == 0
    assert plugin.i_end == 0

    with pytest.raises(ValueError, match="Selected viewer has no display shape"):
        plugin.save_movie(i_start=0, i_end=1)
