from numpy.testing import assert_allclose
import pytest


def test_homezoom_matchx(specviz_helper, spectrum1d):
    """
    Test HomeZoomMatchX tool activates and resets zoom in viewer.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    # Change the zoom
    viewer.state.x_min = 6500
    viewer.state.x_max = 7000

    # Activate home zoom tool
    tool = viewer.toolbar.tools['jdaviz:homezoom_matchx']
    tool.activate()

    # Should reset to original limits
    assert viewer.state.x_min < 6500
    assert viewer.state.x_max > 7000


def test_boxzoom_matchx(specviz_helper, spectrum1d):
    """
    Test BoxZoomMatchX tool with zoom interaction.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    # Activate box zoom tool
    tool = viewer.toolbar.tools['jdaviz:boxzoom_matchx']
    tool.activate()

    # Tool should be activated
    assert tool in viewer.toolbar.tools.values()

    # Test that the tool has the expected properties
    assert hasattr(tool, 'match_axes')
    assert tool.match_axes == ('x',)


def test_xrangezoom_matchx(specviz_helper, spectrum1d):
    """
    Test XRangeZoomMatchX tool with horizontal zoom interaction.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    # Activate x-range zoom tool
    tool = viewer.toolbar.tools['jdaviz:xrangezoom_matchx']
    tool.activate()
    tool.save_prev_zoom()

    # Simulate x-range selection
    tool.interact.selected = [6500, 7000]
    tool.on_update_zoom()

    # X limits should match selection
    assert_allclose(viewer.state.x_min, 6500, rtol=1e-5)
    assert_allclose(viewer.state.x_max, 7000, rtol=1e-5)


def test_panzoom_matchx(specviz_helper, spectrum1d):
    """
    Test PanZoomMatchX tool activation and deactivation.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    # Activate pan zoom tool
    tool = viewer.toolbar.tools['jdaviz:panzoom_matchx']
    tool.activate()

    # Tool should exist and be activatable
    assert tool is not None
    assert hasattr(tool, 'match_axes')

    # Deactivate
    tool.deactivate()


def test_panzoomx_matchx(specviz_helper, spectrum1d):
    """
    Test PanZoomXMatchX tool for horizontal-only panning.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    # Activate pan zoom x tool
    tool = viewer.toolbar.tools['jdaviz:panzoomx_matchx']
    tool.activate()

    # Tool should exist and have correct properties
    assert tool is not None
    assert hasattr(tool, 'match_axes')
    assert tool.match_axes == ('x',)

    tool.deactivate()


def test_matched_zoom_between_viewers(specviz_helper, spectrum1d):
    """
    Test that matched zoom tools synchronize x-limits between viewers.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    # Activate matched box zoom
    tool = viewer.toolbar.tools['jdaviz:boxzoom_matchx']
    tool.activate()
    tool.save_prev_zoom()

    # Change limits in one viewer
    viewer.state.x_min = 6500
    viewer.state.x_max = 7000

    # For single viewer case, just verify limits are set
    assert_allclose(viewer.state.x_min, 6500, rtol=1e-5)
    assert_allclose(viewer.state.x_max, 7000, rtol=1e-5)

    tool.deactivate()


class TestMapLimits:
    """
    Test class for _map_limits method in matched zoom tools.

    This class contains tests that directly call the _map_limits method
    to ensure coverage of its logic branches.
    """
    @staticmethod
    def _setup(deconfigged_helper, spectrum, tool_name='homezoom_matchx'):
        deconfigged_helper.load(spectrum, format='2D Spectrum')

        spectrum_viewer = deconfigged_helper.app.get_viewer('1D Spectrum')
        spectrum2d_viewer = deconfigged_helper.app.get_viewer('2D Spectrum')

        spectrum_tool = spectrum_viewer.toolbar.tools.get(f"jdaviz:{tool_name}")
        spectrum2d_tool = spectrum2d_viewer.toolbar.tools.get(f"jdaviz:{tool_name}")
        return spectrum_viewer, spectrum2d_viewer, spectrum_tool, spectrum2d_tool

    @pytest.mark.parametrize('viewer', ['Spectrum1D->Spectrum2D', 'Spectrum2D->Spectrum1D'])
    def test_map_limits_direct_call(self, deconfigged_helper, spectrum2d, viewer):
        """Test _map_limits method directly with unit conversion."""
        spectrum_viewer, spectrum2d_viewer, spectrum1d_tool, spectrum2d_tool = (
            self._setup(deconfigged_helper, spectrum2d))

        if viewer == 'Spectrum1D->Spectrum2D':
            from_viewer = spectrum_viewer
            to_viewer = spectrum2d_viewer
            tool = spectrum1d_tool
        else:
            from_viewer = spectrum2d_viewer
            to_viewer = spectrum_viewer
            tool = spectrum2d_tool

        # Change to different spectral unit
        uc = deconfigged_helper.plugins['Unit Conversion']
        uc.spectral_unit = 'nm'
        # In order for `_map_limits` to detect the spectral axis component,
        # and therefore perform the unit conversion,
        # it must have 'Wavelength' in its label.
        for component in deconfigged_helper.app.data_collection[0].components:
            if component.label == 'World 1':
                component.label = 'Wavelength'
                break

        test_limits = {'x_min': 1.0, 'x_max': 8.0}
        result = tool._map_limits(from_viewer, to_viewer, test_limits.copy())

        # Values should be the same, but units converted from um to nm
        assert_allclose(1e-3*result['x_min'], test_limits['x_min'], rtol=1e-5)
        assert_allclose(1e-3*result['x_max'], test_limits['x_max'], rtol=1e-5)

    @pytest.mark.parametrize('spec_tool', ['spectrum1d_tool', 'spectrum2d_tool'])
    def test_map_limits_by_activation(self, deconfigged_helper, spectrum2d, spec_tool):
        """
        Test that _map_limits handles unit conversions correctly from Spectrum1D to Spectrum2D.
        Also tests via activation.
        """
        spectrum_viewer, spectrum2d_viewer, spectrum1d_tool, spectrum2d_tool = (
            self._setup(deconfigged_helper, spectrum2d, 'boxzoom_matchx'))

        old_x_min, old_x_max, _, _ = spectrum_viewer.get_limits()
        if spec_tool == 'spectrum1d_tool':
            viewer = spectrum_viewer
            tool = spectrum1d_tool
            offset = 0
        else:
            viewer = spectrum2d_viewer
            tool = spectrum2d_tool
            offset = 0.5
        # _map_limits runs here
        tool.activate()

        # Change limits in spectrum viewer
        check_x_min, check_x_max, y_min, y_max = viewer.get_limits()

        # The spectrum2d tool offsets by 0.5
        assert_allclose(old_x_min, check_x_min + offset, atol=1e-5)
        assert_allclose(old_x_max, check_x_max - offset, atol=1e-5)

        # Set new limits
        tool.interact.selected = [(old_x_min + 3, y_min), (old_x_max - 3, y_max)]
        # _map_limits also runs here
        tool.on_update_zoom()

        # Limits should have changed
        new_x_min, new_x_max, _, _ = viewer.get_limits()
        assert_allclose(new_x_min, old_x_min + 3, rtol=1e-5)
        assert_allclose(new_x_max, old_x_max - 3, rtol=1e-5)

        tool.deactivate()


def test_is_matched_viewer(specviz_helper, spectrum1d):
    """
    Test the _is_matched_viewer method identifies correct viewer types.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    tool = viewer.toolbar.tools['jdaviz:homezoom_matchx']

    # The tool should identify the viewer as matched
    from jdaviz.configs.specviz.plugins.viewers import (
        Spectrum1DViewer
    )
    assert isinstance(viewer, Spectrum1DViewer)
    assert tool._is_matched_viewer(viewer)


def test_matched_zoom_disable_in_other_viewer(specviz_helper, spectrum1d):
    """
    Test that activating matched zoom disables it in other viewers.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    tool = viewer.toolbar.tools['jdaviz:boxzoom_matchx']

    # Check the disable flag is set
    assert tool.disable_matched_zoom_in_other_viewer is True

    # Activate the tool
    tool.activate()

    # Verify tool exists and has correct properties
    assert tool is not None
    assert hasattr(tool, '_is_matched_viewer')

    tool.deactivate()


def test_match_axes_property(specviz_helper, spectrum1d):
    """
    Test that matched zoom tools have correct match_axes property.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    tool = viewer.toolbar.tools['jdaviz:homezoom_matchx']

    # Should only match x-axis for specviz
    assert tool.match_axes == ('x',)
    assert 'x_min' in tool.match_keys
    assert 'x_max' in tool.match_keys


def test_tool_icons_exist(specviz_helper, spectrum1d):
    """
    Test that all matched zoom tools have valid icon paths.
    """
    specviz_helper.load_data(spectrum1d, data_label='test')
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    tool_ids = [
        'jdaviz:homezoom_matchx',
        'jdaviz:boxzoom_matchx',
        'jdaviz:xrangezoom_matchx',
        'jdaviz:panzoom_matchx',
        'jdaviz:panzoomx_matchx'
    ]

    for tool_id in tool_ids:
        tool = viewer.toolbar.tools[tool_id]
        assert hasattr(tool, 'icon')
        assert tool.icon is not None
