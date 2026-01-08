from astropy.io import fits
from astropy.nddata import NDData
import astropy.units as u
import pytest
import numpy as np
from specutils import SpectralRegion
from glue.core.roi import (
    RectangularROI, CircularROI, EllipticalROI,
    CircularAnnulusROI, XRangeROI
)
from glue.core.edit_subset_mode import ReplaceMode


def test_data_menu_toggles(specviz_helper, spectrum1d):
    # NOTE: this test is adopted from core.tests.test_data_menu.test_data_menu_toggles
    # which should be removed once the old data menu is removed from jdaviz

    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    # check that both are enabled in the data menu
    sv = specviz_helper.viewers['spectrum-viewer']
    dm = sv._obj.glue_viewer.data_menu
    assert len(dm._obj.layer_items) == 2
    assert len(dm._obj.visible_layers) == 2

    # disable (hide layer) for second entry
    dm.set_layer_visibility('test2', False)
    assert len(dm._obj.layer_items) == 2
    assert len(dm._obj.visible_layers) == 1

    # add a subset and make sure it appears for the first data entry but not the second
    specviz_helper.plugins['Subset Tools'].import_region(
        SpectralRegion(6000 * spectrum1d.spectral_axis.unit, 6500 * spectrum1d.spectral_axis.unit))

    assert len(dm._obj.layer_items) == 3
    assert len(dm._obj.visible_layers) == 2
    assert len(sv._obj.glue_viewer.layers) == 4
    assert sv._obj.glue_viewer.layers[2].visible is True   # subset corresponding to first (visible)
    assert sv._obj.glue_viewer.layers[3].visible is False  # subset corresponding to second (hidden)

    # enable data layer from menu and subset should also become visible
    dm.toggle_layer_visibility('test2')
    assert np.all([layer.visible for layer in sv._obj.glue_viewer.layers])


def test_data_menu_selection(specviz_helper, spectrum1d):
    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    sv = specviz_helper.viewers['spectrum-viewer']
    dm = sv._obj.glue_viewer.data_menu

    # no selection by default
    assert len(dm._obj.dm_layer_selected) == 0
    assert len(dm.layer.selected) == 0

    # test layer -> UI sync
    dm.layer.selected = dm.layer.choices[0]
    assert len(dm._obj.dm_layer_selected) == len(dm.layer.selected)

    # test UI -> layer sync
    dm._obj.dm_layer_selected = [0, 1]
    assert len(dm._obj.dm_layer_selected) == len(dm.layer.selected)

    # test that sync remains during layer deletion
    dm._obj.dm_layer_selected = [1]
    assert dm.layer.selected == ['test']
    specviz_helper.app.remove_data_from_viewer('spectrum-viewer', "test2")
    specviz_helper.app.data_item_remove("test2")
    assert len(dm._obj.layer_items) == 1
    assert dm._obj.dm_layer_selected == [0]
    assert dm.layer.selected == ['test']


def test_data_menu_add_remove_data(imviz_helper):
    for i in range(3):
        imviz_helper.load_data(np.zeros((2, 2)) + i, data_label=f'image_{i}', show_in_viewer=False)

    dm = imviz_helper.viewers['imviz-0']._obj.glue_viewer.data_menu
    assert len(dm._obj.layer_items) == 0
    assert len(dm.layer.choices) == 0
    assert len(dm._obj.dataset.choices) == 3

    dm.add_data('image_0')
    assert dm.layer.choices == ['image_0']
    assert len(dm._obj.dataset.choices) == 2

    with pytest.raises(ValueError,
                       match="Data labels \\['dne1', 'dne2'\\] not able to be loaded into 'imviz-0'.  Must be one of: \\['image_1', 'image_2'\\]"):  # noqa
        dm.add_data('dne1', 'dne2')

    dm.add_data('image_1', 'image_2')
    assert len(dm.layer.choices) == 3
    assert len(dm._obj.dataset.choices) == 0

    dm.layer.selected = ['image_0']
    dm.remove_from_viewer()
    assert len(dm.layer.choices) == 2
    assert len(dm._obj.dataset.choices) == 1

    dm.layer.selected = ['image_1']
    dm.remove_from_app()
    assert len(dm.layer.choices) == 1
    assert len(dm._obj.dataset.choices) == 1


def test_remove_all_data_cubeviz(cubeviz_helper, image_cube_hdu_obj_microns):
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label="test")
    dm1 = cubeviz_helper.viewers['flux-viewer']._obj.glue_viewer.data_menu
    dm2 = cubeviz_helper.viewers['uncert-viewer']._obj.glue_viewer.data_menu
    dm3 = cubeviz_helper.viewers['spectrum-viewer']._obj.glue_viewer.data_menu

    sp = cubeviz_helper.plugins['Subset Tools']
    sp.import_region(SpectralRegion(4.8 * u.um,
                                    5 * u.um),
                     combination_mode='new')

    # Remove all data from all viewers to make sure plugins respond appropriately
    # This would previously raise a traceback from the data menu and/or aperture photometry
    dm1.layer.selected = ['test[FLUX]']
    dm1.remove_from_viewer()
    dm2.layer.selected = ['test[ERR]']
    dm2.remove_from_viewer()
    dm3.layer.selected = ['Spectrum (sum)', 'Subset 1']
    dm3.remove_from_viewer()

    for plg in ('Moment Maps', 'Line Analysis', 'Line Lists'):
        assert "unavailable" in cubeviz_helper.plugins[plg]._obj.disabled_msg


def test_data_menu_create_subset(imviz_helper):
    imviz_helper.load_data(np.zeros((2, 2)), data_label='image', show_in_viewer=True)

    dm = imviz_helper.viewers['imviz-0']._obj.glue_viewer.data_menu
    assert imviz_helper.app.session.edit_subset_mode.edit_subset == []

    dm.create_subset('circle')
    assert imviz_helper.app.session.edit_subset_mode.edit_subset == []
    assert imviz_helper.viewers['imviz-0']._obj.glue_viewer.toolbar.active_tool_id == 'bqplot:truecircle'  # noqa


def test_data_menu_remove_subset(specviz_helper, spectrum1d):
    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    dm = specviz_helper.viewers['spectrum-viewer']._obj.glue_viewer.data_menu
    sp = specviz_helper.plugins['Subset Tools']

    sp.import_region(SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                                    6100 * spectrum1d.spectral_axis.unit),
                     combination_mode='new')
    sp.import_region(SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                                    6100 * spectrum1d.spectral_axis.unit),
                     combination_mode='new')

    assert dm.layer.choices == ['Subset 2', 'Subset 1', 'test2', 'test']
    dm.layer.selected = ['Subset 1']
    dm.remove_from_viewer()

    # subset visibility is set to false, but still appears in menu (unlike removing data)
    assert dm.layer.choices == ['Subset 2', 'Subset 1', 'test2', 'test']
    assert dm._obj.layer_items[1]['label'] == 'Subset 1'
    # TODO: sometimes appearing as mixed right now, known bug
    assert dm._obj.layer_items[1]['visible'] is not True

    # selection should not have changed by removing subset from viewer
    assert dm.layer.selected == ['Subset 1']
    dm.remove_from_app()
    # TODO: not quite sure why this isn't passing, seems to
    # work on local tests, so may just be async?
    # assert dm.layer.choices == ['test', 'test2', 'Subset 2']


def test_data_menu_dq_layers(imviz_helper):
    hdu_data = fits.ImageHDU(np.zeros(shape=(2, 2)))
    hdu_data.name = 'SCI'
    hdu_dq = fits.ImageHDU(np.zeros(shape=(2, 2), dtype=np.int32))
    hdu_dq.name = 'DQ'
    data = fits.HDUList([fits.PrimaryHDU(), hdu_data, hdu_dq])

    imviz_helper.load_data(data, data_label="image", ext=('SCI', 'DQ'), show_in_viewer=True)

    dm = imviz_helper.viewers['imviz-0']._obj.glue_viewer.data_menu
    assert dm.layer.choices == ['image[SCI,1]', 'image[DQ,1]']
    assert len(dm._obj.visible_layers) == 2

    # turning off image (parent) data-layer should also turn off DQ
    dm.set_layer_visibility('image[SCI,1]', False)
    assert len(dm._obj.visible_layers) == 0

    # turning on image (parent) should leave DQ off
    dm.set_layer_visibility('image[SCI,1]', True)
    assert len(dm._obj.visible_layers) == 1

    # turning on DQ (child, when parent off) should show parent
    dm.set_layer_visibility('image[SCI,1]', False)
    dm.set_layer_visibility('image[DQ,1]', True)
    assert len(dm._obj.visible_layers) == 2


@pytest.mark.xfail(reason="known issue")
def test_data_menu_subset_appearance(specviz_helper, spectrum1d):
    # NOTE: this test is similar to above - the subset is appearing in time IF there
    # are two data entries, but not in this case with just one
    specviz_helper.load_data(spectrum1d, data_label="test")

    dm = specviz_helper.viewers['spectrum-viewer']._obj.glue_viewer.data_menu
    sp = specviz_helper.plugins['Subset Tools']

    sp.import_region(SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                                    6100 * spectrum1d.spectral_axis.unit))

    # AssertionError: assert ['Subset 1', 'test'] == ['test', 'Subset 1']
    assert dm.layer.choices == ['test', 'Subset 1']


def test_data_menu_view_info(specviz_helper, spectrum1d):
    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    dm = specviz_helper.viewers['spectrum-viewer']._obj.glue_viewer.data_menu
    mp = specviz_helper.plugins['Metadata']
    sp = specviz_helper.plugins['Subset Tools']

    sp.import_region(SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                                    6100 * spectrum1d.spectral_axis.unit),
                     combination_mode='new')
    sp.import_region(SpectralRegion(6200 * spectrum1d.spectral_axis.unit,
                                    6300 * spectrum1d.spectral_axis.unit),
                     combination_mode='new')

    assert dm.layer.choices == ['Subset 2', 'Subset 1', 'test2', 'test']

    dm.layer.selected = ["test2"]
    dm.view_info()
    assert mp.dataset.selected == "test2"

    dm.layer.selected = ["Subset 2"]
    dm.view_info()
    assert sp.subset.selected == "Subset 2"

    dm.layer.selected = ["test", "test2"]
    with pytest.raises(ValueError, match="Only one layer can be selected to view info"):
        dm.view_info()


class TestResizeSubset:
    """
    Test suite for DataMenu resize subset functionality.
    """
    @pytest.fixture(autouse=True)
    def _init(self, imviz_helper, specviz_helper, spectrum1d):
        """
        Autouse fixture to attach the shared helper to the test instance.
        """
        self.imviz_helper = imviz_helper
        self.imviz_helper.load_data(np.zeros((10, 10)), data_label='image', show_in_viewer=True)
        self.imviz_viewer = self.imviz_helper.default_viewer._obj.glue_viewer
        self.imviz_dm = self.imviz_viewer.data_menu
        self.imviz_subset_tools = self.imviz_helper.plugins['Subset Tools']

        self.specviz_helper = specviz_helper
        self.specviz_helper.load(spectrum1d, data_label="Spectrum 1D")
        self.specviz_viewer = self.specviz_helper.app.get_viewer('spectrum-viewer')
        self.specviz_dm = self.specviz_viewer.data_menu
        self.specviz_subset_tools = self.specviz_helper.plugins['Subset Tools']

    def test_allow_resize_subset_in_viewer(self):
        """
        Test _allow_resize_subset_in_viewer with single and composite subsets.
        """
        # Create a circular subset
        self.imviz_viewer.apply_roi(CircularROI(xc=5, yc=5, radius=2))

        # Test without any subsets selected (returns None_
        assert self.imviz_dm._obj._allow_resize_subset_in_viewer() is None
        self.imviz_dm.layer.selected = []
        assert self.imviz_dm._obj._allow_resize_subset_in_viewer() is None

        # Select the subset
        self.imviz_dm.layer.selected = ['Subset 1']

        # Trigger the allow resize check
        self.imviz_dm._obj._allow_resize_subset_in_viewer()

        # Should be enabled for simple ROI
        assert self.imviz_dm._obj.subset_resize_in_viewer_enabled is True

        # Combine to create composite subset
        self.imviz_subset_tools.combination_mode = 'or'
        self.imviz_subset_tools.subset.selected = 'Subset 1'
        self.imviz_viewer.apply_roi(CircularROI(xc=5, yc=5, radius=1))

        # Select the composite subset
        self.imviz_dm.layer.selected = ['Subset 1']

        # Trigger the allow resize check
        self.imviz_dm._obj._allow_resize_subset_in_viewer()

        # Should be disabled for composite ROI
        assert self.imviz_dm._obj.subset_resize_in_viewer_enabled is False

    @pytest.mark.parametrize(
        ("roi", "tool_id"), [
            (CircularROI(xc=5, yc=5, radius=2), 'bqplot:truecircle'),
            (RectangularROI(xmin=2, xmax=7, ymin=3, ymax=8), 'bqplot:rectangle'),
            (EllipticalROI(xc=5, yc=5, radius_x=2, radius_y=3), 'bqplot:ellipse'),
            (CircularAnnulusROI(xc=5, yc=5, inner_radius=1, outer_radius=3), 'bqplot:circannulus')])
    def test_resize_subset_in_viewer_image_rois(self, roi, tool_id):
        """
        Test resize_subset_in_viewer functionality with various image ROIs.
        """
        # Create a circular subset
        self.imviz_viewer.apply_roi(roi)

        # Select the subset for resizing
        self.imviz_dm.layer.selected = ['Subset 1']

        # Resize the subset
        self.imviz_dm.resize_subset_in_viewer()

        # Verify that the correct tool is activated
        assert self.imviz_viewer.toolbar.active_tool_id == tool_id

        # Verify that we're in replace mode
        assert self.imviz_helper.app.session.edit_subset_mode.mode == ReplaceMode

        # Verify that the correct subset is being edited
        subset_grp = [sg for sg in self.imviz_helper.app.data_collection.subset_groups
                      if sg.label == 'Subset 1']
        assert self.imviz_helper.app.session.edit_subset_mode.edit_subset == subset_grp

    @pytest.mark.parametrize('roi', [XRangeROI(min=6000, max=6500),
                                     SpectralRegion(6000 * u.Angstrom, 6500 * u.Angstrom)])
    def test_resize_subset_in_viewer_xrange_roi(self, roi):
        """
        Test resize_subset_in_viewer functionality with an XRange ROI and
        Spectral Region (implicitly) converted to XRange ROI.
        """
        if isinstance(roi, XRangeROI):
            # Create an XRange subset
            self.specviz_viewer.apply_roi(roi)
        elif isinstance(roi, SpectralRegion):
            self.specviz_subset_tools.import_region(roi)

        # Select and resize
        self.specviz_dm.layer.selected = ['Subset 1']
        self.specviz_dm.resize_subset_in_viewer()

        # Verify that the correct tool is activated
        assert self.specviz_viewer.toolbar.active_tool_id == 'bqplot:xrange'
        assert self.specviz_helper.app.session.edit_subset_mode.mode == ReplaceMode

    def test_resize_subset_in_viewer_errors(self):
        """
        Test that resize_subset_in_viewer raises errors where expected.
        """
        # Create two subsets
        self.imviz_viewer.apply_roi(CircularROI(xc=3, yc=3, radius=2))
        self.imviz_subset_tools.combination_mode = 'new'
        self.imviz_viewer.apply_roi(CircularROI(xc=7, yc=7, radius=2))

        # Select both subsets
        self.imviz_dm.layer.selected = ['Subset 1', 'Subset 2']

        # Should raise error
        msg = 'Only one layer can be selected to resize subset.'
        with pytest.raises(ValueError, match=msg):
            self.imviz_dm.resize_subset_in_viewer()

        # Select data layer instead of subset
        self.imviz_dm.layer.selected = ['image']

        # Should raise error
        msg = 'Selected layer is not a subset.'
        with pytest.raises(ValueError, match=msg):
            self.imviz_dm.resize_subset_in_viewer()

        # Select the subset again
        self.imviz_dm.layer.selected = ['Subset 1']

        # Retrieve the subset group and replace its subset_state with a
        # mock object that is not a RoiSubsetState/RangeSubsetState to
        # simulate an unsupported ROI.
        subset_grp = [sg for sg in self.imviz_helper.app.data_collection.subset_groups
                      if sg.label == 'Subset 1']

        # Replace the subset_state with a plain object (unsupported)
        subset_grp[0].subset_state = object()

        # Try to resize and assert the specific error message
        msg = 'Selected subset does not have a supported ROI.'
        with pytest.raises(ValueError, match=msg):
            self.imviz_dm.resize_subset_in_viewer()


def test_catalog_excluded_from_layer_reordering(imviz_helper, image_2d_wcs,
                                                sky_coord_only_source_catalog):
    """
    Test that catalog layers are excluded from zordermanagement in image viewers.

    To do this, load an image, align by WCS, then load a catalog. The catalog
    layer should always be at the top of the layer stack. Then, add a subset to
    ensure the catalog layer remains on top. The addition of a 'Default Orientation'
    and a subset layer will test the reordering functionality of the data menu, and
    ensure that catalog layers are excluded from reordering and always remain on top.
    """

    data = NDData(np.ones((128, 128)), wcs=image_2d_wcs)
    imviz_helper.load(data)

    imviz_helper.plugins['Orientation'].align_by = 'WCS'

    # load catalog
    imviz_helper.app.state.catalogs_in_dc = True
    imviz_helper.load(sky_coord_only_source_catalog, data_label='catalog')

    # load catalog. with the presence of a 'Default Orientation' layer that is
    # NOT listed in the data menu, loading a catalog will cause the layer
    # reordering logic in data_menu to run, and scatter layers should remain unchanged
    layers = imviz_helper.default_viewer.data_menu._obj._viewer.layers
    assert layers[-1].layer.label == 'catalog'

    # Now add a subset and ensure catalog layer remains on top
    subset_tools = imviz_helper.plugins['Subset Tools']
    subset_tools.import_region(CircularROI(xc=0, yc=0, radius=1))
    assert layers[-1].layer.label == 'catalog'
