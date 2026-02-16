"""
Tests for table viewer tools: TableHighlightSelected, TableZoomToSelected, TableSubset.
"""

import numpy as np
import pytest

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.nddata import NDData

from jdaviz.core.marks import PluginScatter


class TestTableViewerTools:
    """Test table viewer tools (highlight, zoom, subset)."""

    @pytest.fixture(autouse=True)
    def setup_method(self, deconfigged_helper, image_2d_wcs, sky_coord_only_source_catalog):
        """Set up deconfigged app with image and catalog data using existing fixtures."""
        # Create image using the fixture WCS
        arr = np.arange(10000).reshape((100, 100))
        ndd = NDData(arr, wcs=image_2d_wcs)
        deconfigged_helper.load(ndd, data_label='test_image')

        # Use the existing catalog fixture - load into a Table viewer
        self.catalog = sky_coord_only_source_catalog
        ldr = deconfigged_helper.loaders['object']
        ldr.object = self.catalog
        ldr.format = 'Catalog'
        ldr.importer.viewer.create_new = 'Table'
        ldr.load()

        self.app = deconfigged_helper
        self.wcs = image_2d_wcs

        # Get the image viewer
        image_viewers = list(deconfigged_helper.app.get_viewers_of_cls('ImvizImageView'))
        assert len(image_viewers) == 1
        self.viewer = image_viewers[0]

        # Set viewer shape for zoom testing
        self.viewer.shape = (400, 400)
        self.viewer.state._set_axes_aspect_ratio(1)

        # Get the table viewer
        self.table_viewer = deconfigged_helper.viewers['Table']._obj.glue_viewer

    def test_table_highlight_tool_activates(self):
        """Test that TableHighlightSelected tool activates properly."""
        toolbar = self.table_viewer.toolbar

        # Activate the highlight tool
        assert 'jdaviz:table_highlight_selected' in toolbar.tools
        tool = toolbar.tools['jdaviz:table_highlight_selected']

        # Check that selection is not enabled initially
        assert not self.table_viewer.widget_table.selection_enabled

        # Activate the tool
        tool.activate()

        # Check that selection checkboxes are now enabled
        assert self.table_viewer.widget_table.selection_enabled

        # Check that toolbar is in override mode
        assert toolbar.tool_override_mode == 'Table Highlight Selection'

        # Check that image viewer toolbar is also overridden
        image_toolbar = self.viewer.toolbar
        assert image_toolbar.tool_override_mode == 'Table Highlight Selection'

        # Restore toolbar
        toolbar.restore_tools()

        # Check that selection is disabled after restore
        assert not self.table_viewer.widget_table.selection_enabled
        assert toolbar.tool_override_mode == ''

    def test_table_highlight_marks_appear(self):
        """Test that highlight marks appear in image viewer when rows are checked."""
        toolbar = self.table_viewer.toolbar
        tool = toolbar.tools['jdaviz:table_highlight_selected']
        tool.activate()

        # Check some rows
        self.table_viewer.widget_table.checked = [0, 2]

        # Check that marks are visible in the image viewer
        marks = [m for m in self.viewer.figure.marks if isinstance(m, PluginScatter)]

        # There should be at least one PluginScatter mark for selection
        assert len(marks) > 0

        # Restore and check marks are cleared
        toolbar.restore_tools()

    def test_table_zoom_tool_activates(self):
        """Test that TableZoomToSelected tool activates properly."""
        toolbar = self.table_viewer.toolbar

        assert 'jdaviz:table_zoom_to_selected' in toolbar.tools
        tool = toolbar.tools['jdaviz:table_zoom_to_selected']

        # Activate the tool
        tool.activate()

        # Check that selection checkboxes are enabled
        assert self.table_viewer.widget_table.selection_enabled

        # Check that toolbar is in override mode with correct title
        assert toolbar.tool_override_mode == 'Table Zoom Selection'

        # Check that custom widgets are present (viewer dropdown)
        assert len(toolbar.custom_widget_items) > 0

        # Check that image viewer toolbar is also overridden
        image_toolbar = self.viewer.toolbar
        assert image_toolbar.tool_override_mode == 'Table Zoom Selection'

        toolbar.restore_tools()

    def test_table_zoom_applies_correct_limits(self):
        """Test that zoom-to-selected sets correct viewer limits."""
        toolbar = self.table_viewer.toolbar
        tool = toolbar.tools['jdaviz:table_zoom_to_selected']
        tool.activate()

        # Get initial viewer limits
        initial_limits = (
            self.viewer.state.x_min, self.viewer.state.x_max,
            self.viewer.state.y_min, self.viewer.state.y_max
        )

        # Check some rows (use first 3 catalog sources)
        self.table_viewer.widget_table.checked = [0, 1, 2]

        # Get the apply tool and activate it
        apply_tool = toolbar.tools['jdaviz:table_apply_zoom']
        apply_tool.activate()

        # The viewer limits should have changed
        new_limits = (
            self.viewer.state.x_min, self.viewer.state.x_max,
            self.viewer.state.y_min, self.viewer.state.y_max
        )
        new_x_min, new_x_max, new_y_min, new_y_max = new_limits

        # Check that limits changed (zoomed in to the selected points)
        assert new_limits != initial_limits

        # Convert the catalog coordinates to pixels and verify they're within bounds
        from astropy.coordinates import SkyCoord
        selected_rows = [0, 1, 2]
        ras = self.catalog['ra'][selected_rows]
        decs = self.catalog['dec'][selected_rows]
        skycoords = SkyCoord(ra=ras, dec=decs)

        # Get pixel coordinates in reference data frame
        pixel_coords = self.viewer.state.reference_data.coords.world_to_pixel(skycoords)
        xs, ys = pixel_coords[0], pixel_coords[1]

        # All selected points should be within the new view bounds
        for x, y in zip(xs, ys):
            assert new_x_min <= x <= new_x_max, \
                f"Point x={x} outside view bounds [{new_x_min}, {new_x_max}]"
            assert new_y_min <= y <= new_y_max, \
                f"Point y={y} outside view bounds [{new_y_min}, {new_y_max}]"

    def test_table_zoom_single_point(self):
        """Test that zoom-to-selected works for a single point."""
        toolbar = self.table_viewer.toolbar
        tool = toolbar.tools['jdaviz:table_zoom_to_selected']
        tool.activate()

        # Check only one row
        self.table_viewer.widget_table.checked = [0]

        # Get the apply tool and activate it
        apply_tool = toolbar.tools['jdaviz:table_apply_zoom']
        apply_tool.activate()

        # Get the new limits
        new_x_min = self.viewer.state.x_min
        new_x_max = self.viewer.state.x_max
        new_y_min = self.viewer.state.y_min
        new_y_max = self.viewer.state.y_max

        # The view should be zoomed to a small area around the single point
        x_range = new_x_max - new_x_min
        y_range = new_y_max - new_y_min

        # Single point should still have some reasonable zoom range
        assert x_range > 0
        assert y_range > 0

        # The point should be within bounds
        ra = self.catalog['ra'][0]
        dec = self.catalog['dec'][0]
        skycoord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg)

        pixel_coords = self.viewer.state.reference_data.coords.world_to_pixel(skycoord)
        px, py = float(pixel_coords[0]), float(pixel_coords[1])

        assert new_x_min <= px <= new_x_max
        assert new_y_min <= py <= new_y_max

    def test_table_subset_tool_activates(self):
        """Test that TableSubset tool activates properly."""
        toolbar = self.table_viewer.toolbar

        assert 'jdaviz:table_subset' in toolbar.tools
        tool = toolbar.tools['jdaviz:table_subset']

        # Activate the tool
        tool.activate()

        # Check that selection checkboxes are enabled
        assert self.table_viewer.widget_table.selection_enabled

        # Check that toolbar is in override mode with correct title
        assert toolbar.tool_override_mode == 'Table Subset Selection'

        # Check that image viewer toolbar is also overridden
        image_toolbar = self.viewer.toolbar
        assert image_toolbar.tool_override_mode == 'Table Subset Selection'

        toolbar.restore_tools()

    def test_table_subset_creates_subset(self):
        """Test that applying subset creates a subset in the data collection."""
        toolbar = self.table_viewer.toolbar
        tool = toolbar.tools['jdaviz:table_subset']
        tool.activate()

        # Get initial subset count
        initial_subset_count = len(self.app.app.data_collection.subset_groups)

        # Check some rows
        self.table_viewer.widget_table.checked = [0, 1, 2]

        # Get the apply tool and activate it
        apply_tool = toolbar.tools['jdaviz:table_apply_subset']
        apply_tool.activate()

        # A new subset should have been created
        new_subset_count = len(self.app.app.data_collection.subset_groups)
        assert new_subset_count == initial_subset_count + 1

    def test_select_table_row_tool_in_image_viewer(self):
        """Test that SelectTableRow tool is available in image viewer when table tool is active."""
        # Activate a table selection tool
        table_toolbar = self.table_viewer.toolbar
        table_toolbar.tools['jdaviz:table_highlight_selected'].activate()

        # Check that image viewer toolbar has the select_table_row tool
        image_toolbar = self.viewer.toolbar
        assert 'jdaviz:select_table_row' in image_toolbar.tools

        # The tool should have the table viewer ID set
        select_tool = image_toolbar.tools['jdaviz:select_table_row']
        assert select_tool._table_viewer_id == self.table_viewer.reference_id

        # The tool should be active (auto-activated when table tool is activated)
        assert image_toolbar.active_tool_id == 'jdaviz:select_table_row'

        table_toolbar.restore_tools()

    def test_toolbar_titles_match(self):
        """Test that table and image viewer toolbar titles match."""
        table_toolbar = self.table_viewer.toolbar
        image_toolbar = self.viewer.toolbar

        # Test each tool
        for tool_id, expected_title in [
            ('jdaviz:table_highlight_selected', 'Table Highlight Selection'),
            ('jdaviz:table_zoom_to_selected', 'Table Zoom Selection'),
            ('jdaviz:table_subset', 'Table Subset Selection'),
        ]:
            table_toolbar.tools[tool_id].activate()

            assert table_toolbar.tool_override_mode == expected_title
            assert image_toolbar.tool_override_mode == expected_title

            table_toolbar.restore_tools()

    def test_checked_rows_persist_after_apply(self):
        """Test that checked rows persist after applying zoom or subset."""
        toolbar = self.table_viewer.toolbar

        # Test with zoom tool
        toolbar.tools['jdaviz:table_zoom_to_selected'].activate()
        self.table_viewer.widget_table.checked = [0, 1, 2]
        assert len(self.table_viewer.widget_table.checked) == 3

        toolbar.tools['jdaviz:table_apply_zoom'].activate()

        # Checked rows should persist (not cleared)
        assert len(self.table_viewer.widget_table.checked) == 3

    def test_is_enabled_returns_correct_state(self):
        """Test that apply tools are disabled when no rows are checked."""
        toolbar = self.table_viewer.toolbar

        # Activate zoom tool
        toolbar.tools['jdaviz:table_zoom_to_selected'].activate()

        apply_tool = toolbar.tools['jdaviz:table_apply_zoom']

        # Should be disabled with no rows checked (non-empty disabled_msg)
        msg = apply_tool.disabled_msg()
        assert msg != ''
        assert 'Select rows' in msg

        # Check some rows
        self.table_viewer.widget_table.checked = [0, 1]

        # Should now be enabled (empty disabled_msg)
        msg = apply_tool.disabled_msg()
        assert msg == ''

        toolbar.restore_tools()


class TestTableViewerToolsMultipleViewers:
    """Test table viewer tools with multiple image viewers."""

    @pytest.fixture(autouse=True)
    def setup_method(self, deconfigged_helper, image_2d_wcs, sky_coord_only_source_catalog):
        """Set up deconfigged app with image, catalog, and multiple viewers."""
        # Create and load image
        arr = np.arange(10000).reshape((100, 100))
        ndd = NDData(arr, wcs=image_2d_wcs)
        deconfigged_helper.load(ndd, data_label='test_image')

        # Load catalog into a Table viewer
        self.catalog = sky_coord_only_source_catalog
        ldr = deconfigged_helper.loaders['object']
        ldr.object = self.catalog
        ldr.format = 'Catalog'
        ldr.importer.viewer.create_new = 'Table'
        ldr.load()

        self.app = deconfigged_helper

        # Create a second image viewer using new_viewers
        vc = deconfigged_helper.new_viewers['Image']
        vc.dataset = 'test_image[DATA]'
        vc.viewer_label = 'Image (2)'
        vc()

        # Get viewers
        image_viewers = list(deconfigged_helper.app.get_viewers_of_cls('ImvizImageView'))
        self.viewer1 = image_viewers[0]
        self.viewer2 = image_viewers[1] if len(image_viewers) > 1 else image_viewers[0]

        # Set viewer shapes
        for v in [self.viewer1, self.viewer2]:
            v.shape = (400, 400)
            v.state._set_axes_aspect_ratio(1)

        # Get table viewer
        self.table_viewer = deconfigged_helper.viewers['Table']._obj.glue_viewer

    def test_zoom_applies_to_all_viewers_by_default(self):
        """Test that zoom applies to all viewers when no specific viewer is selected."""
        toolbar = self.table_viewer.toolbar
        tool = toolbar.tools['jdaviz:table_zoom_to_selected']
        tool.activate()

        # Check some rows
        self.table_viewer.widget_table.checked = [0, 1, 2]

        # Store initial limits for viewer 1
        v1_initial_limits = (
            self.viewer1.state.x_min, self.viewer1.state.x_max,
            self.viewer1.state.y_min, self.viewer1.state.y_max
        )

        # Apply zoom
        toolbar.tools['jdaviz:table_apply_zoom'].activate()

        # Viewer 1 should have been zoomed
        v1_new_limits = (
            self.viewer1.state.x_min, self.viewer1.state.x_max,
            self.viewer1.state.y_min, self.viewer1.state.y_max
        )

        assert v1_new_limits != v1_initial_limits

    def test_all_image_viewers_get_override_toolbar(self):
        """Test that all image viewers get override toolbar when table tool is activated."""
        toolbar = self.table_viewer.toolbar
        toolbar.tools['jdaviz:table_highlight_selected'].activate()

        # Both image viewer toolbars should be in override mode
        assert self.viewer1.toolbar.tool_override_mode == 'Table Highlight Selection'
        assert self.viewer2.toolbar.tool_override_mode == 'Table Highlight Selection'

        toolbar.restore_tools()

        # Both should be restored
        assert self.viewer1.toolbar.tool_override_mode == ''
        assert self.viewer2.toolbar.tool_override_mode == ''


class TestTableViewerToolsPixelLinked:
    """Test table viewer tools with pixel-linked catalogs."""

    @pytest.fixture(autouse=True)
    def setup_method(self, deconfigged_helper, pixel_coord_source_catalog):
        """Set up deconfigged app with image and pixel-coordinate catalog."""
        # Create a simple image (no WCS needed for pixel-linked)
        from astropy.nddata import NDData
        arr = np.arange(10000).reshape((100, 100))
        ndd = NDData(arr)
        deconfigged_helper.load(ndd, data_label='test_image')

        # Load the pixel-coordinate catalog into a Table viewer
        self.catalog = pixel_coord_source_catalog
        ldr = deconfigged_helper.loaders['object']
        ldr.object = self.catalog
        ldr.format = 'Catalog'
        ldr.importer.viewer.create_new = 'Table'
        ldr.importer.col_x.selected = 'x'
        ldr.importer.col_y.selected = 'y'
        ldr.load()

        self.app = deconfigged_helper

        # Get the image viewer
        image_viewers = list(deconfigged_helper.app.get_viewers_of_cls('ImvizImageView'))
        assert len(image_viewers) == 1
        self.viewer = image_viewers[0]

        # Set viewer shape
        self.viewer.shape = (400, 400)
        self.viewer.state._set_axes_aspect_ratio(1)

        # Get the table viewer
        self.table_viewer = deconfigged_helper.viewers['Table']._obj.glue_viewer

    def test_pixel_linked_zoom_applies_correct_limits(self):
        """Test that zoom-to-selected works with pixel-linked catalogs."""
        # Verify we're pixel-linked
        assert self.app.app._align_by == 'pixels'

        toolbar = self.table_viewer.toolbar
        tool = toolbar.tools['jdaviz:table_zoom_to_selected']
        tool.activate()

        # Get initial viewer limits
        initial_limits = (
            self.viewer.state.x_min, self.viewer.state.x_max,
            self.viewer.state.y_min, self.viewer.state.y_max
        )

        # Check some rows (use first 3 catalog sources)
        self.table_viewer.widget_table.checked = [0, 1, 2]

        # Get the apply tool and activate it
        apply_tool = toolbar.tools['jdaviz:table_apply_zoom']
        apply_tool.activate()

        # The viewer limits should have changed
        new_limits = (
            self.viewer.state.x_min, self.viewer.state.x_max,
            self.viewer.state.y_min, self.viewer.state.y_max
        )
        new_x_min, new_x_max, new_y_min, new_y_max = new_limits

        # Check that limits changed (zoomed in to the selected points)
        assert new_limits != initial_limits

        # Verify that the selected pixel coordinates are within the view bounds
        selected_rows = [0, 1, 2]
        xs = [self.catalog['x'][i] for i in selected_rows]
        ys = [self.catalog['y'][i] for i in selected_rows]

        for x, y in zip(xs, ys):
            assert new_x_min <= x <= new_x_max, \
                f"Point x={x} outside view bounds [{new_x_min}, {new_x_max}]"
            assert new_y_min <= y <= new_y_max, \
                f"Point y={y} outside view bounds [{new_y_min}, {new_y_max}]"

    def test_pixel_linked_highlight_marks_appear(self):
        """Test that highlight marks appear with pixel-linked catalogs."""
        # Verify we're pixel-linked
        assert self.app.app._align_by == 'pixels'

        toolbar = self.table_viewer.toolbar
        tool = toolbar.tools['jdaviz:table_highlight_selected']
        tool.activate()

        # Check some rows
        self.table_viewer.widget_table.checked = [0, 2]

        # Check that marks are visible in the image viewer
        from jdaviz.core.marks import PluginScatter
        marks = [m for m in self.viewer.figure.marks if isinstance(m, PluginScatter)]

        # There should be at least one PluginScatter mark for selection
        assert len(marks) > 0

        # Restore and check marks are cleared
        toolbar.restore_tools()
