import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.nddata import NDData
from regions import CirclePixelRegion, PixCoord, PolygonSkyRegion

from jdaviz.app import PrivateApplication
from jdaviz.core.config import get_configuration
from jdaviz.core.marks import RegionOverlay
from jdaviz.configs.imviz.helper import Imviz
from jdaviz.configs.imviz.plugins.viewers import ImvizImageView
from jdaviz.configs.imviz.tests.utils import (
    BaseImviz_WCS_NoWCS, create_example_gwcs
)
from jdaviz.conftest import _image_hdu_wcs

from numpy.testing import assert_allclose


# should this be deprecated since deconfigged doesn't spawn viewers without data?
@pytest.mark.parametrize(
    ('desired_name', 'actual_name'),
    [(None, 'imviz-1'),
     ('babylon-5', 'babylon-5')])
def test_create_destroy_viewer(imviz_helper, desired_name, actual_name):
    assert imviz_helper._app.get_viewer_ids() == ['imviz-0']

    viewer = imviz_helper.create_image_viewer(viewer_name=desired_name)
    viewer_names = sorted(['imviz-0', actual_name])
    assert viewer.top_visible_data_label == ''
    assert isinstance(viewer, ImvizImageView)
    assert viewer is imviz_helper._app._viewer_store.get(actual_name), list(imviz_helper._app._viewer_store.keys())  # noqa
    assert imviz_helper._app.get_viewer_ids() == viewer_names

    # Make sure plugins that store viewer_items are updated.
    assert sorted(imviz_helper.plugins['Compass'].viewer.labels) == viewer_names

    po = imviz_helper.plugins['Plot Options']
    po.viewer_multiselect = True
    po.layer_multiselect = True
    po.viewer = viewer_names

    imviz_helper.destroy_viewer(actual_name)
    assert imviz_helper._app.get_viewer_ids() == ['imviz-0']
    assert po.viewer.selected == ['imviz-0']
    assert po.viewer.labels == ['imviz-0']


def test_create_viewer_align_by_wcs(deconfigged_helper, image_2d_wcs):
    data = NDData(np.ones((128, 128)) * u.nJy, wcs=image_2d_wcs)
    deconfigged_helper.load(data, data_label='my_data', format='Image')

    new_viewer = deconfigged_helper.new_viewers['Image']
    new_viewer()
    dm = deconfigged_helper.viewers['Image (1)'].data_menu
    dm.add_data('my_data[DATA]')

    assert not dm._obj.orientation_align_by_wcs

    deconfigged_helper.plugins['Orientation'].align_by = 'WCS'

    assert dm._obj.orientation_align_by_wcs
    assert dm.orientation.selected == 'Default orientation'


def test_align_by_wcs_create_viewer(deconfigged_helper, image_2d_wcs):
    data = NDData(np.ones((128, 128)) * u.nJy, wcs=image_2d_wcs)
    deconfigged_helper.load(data, data_label='my_data', format='Image')

    deconfigged_helper.plugins['Orientation'].align_by = 'WCS'

    new_viewer = deconfigged_helper.new_viewers['Image']
    new_viewer()
    dm = deconfigged_helper.viewers['Image (1)'].data_menu
    dm.add_data('my_data[DATA]')

    assert dm._obj.orientation_align_by_wcs
    assert dm.orientation.selected == 'Default orientation'


# should this be deprecated since deconfigged_helper doesn't spawn viewers automatically?
def test_get_viewer_created(imviz_helper):
    # This viewer has no reference but has ID.
    viewer1 = imviz_helper.create_image_viewer()
    viewer2 = imviz_helper._app.get_viewer('imviz-1')
    assert viewer1 is viewer2


# should this be deprecated since deconfigged_helper doesn't spawn viewers automatically?
def test_destroy_viewer_invalid(imviz_helper):
    assert imviz_helper._app.get_viewer_ids() == ['imviz-0']

    imviz_helper.destroy_viewer('foo')
    assert imviz_helper._app.get_viewer_ids() == ['imviz-0']

    with pytest.raises(ValueError, match='cannot be destroyed'):
        imviz_helper.destroy_viewer('imviz-0')
    assert imviz_helper._app.get_viewer_ids() == ['imviz-0']


def test_destroy_viewer_with_subset(deconfigged_helper):
    """Regression test for https://github.com/spacetelescope/jdaviz/issues/1614"""
    arr = np.ones((10, 10))
    deconfigged_helper.load(arr, data_label='my_array', format='Image')

    # Create a second viewer.
    new_viewer = deconfigged_helper.new_viewers['Image']
    new_viewer()

    # Add existing data to second viewer.
    deconfigged_helper._app.add_data_to_viewer('Image (1)', 'my_array')

    # Create a Subset.
    reg = CirclePixelRegion(center=PixCoord(x=4, y=4), radius=2)
    deconfigged_helper.plugins['Subset Tools'].import_region(reg)

    # Remove the second viewer.
    deconfigged_helper._app.vue_destroy_viewer_item('Image (1)')

    # Delete the Subset: Should have no traceback.
    deconfigged_helper._app.delete_subsets('Subset 1')


def test_mastviz_config():
    """Use case from https://github.com/spacetelescope/jdaviz/issues/1037"""

    # create a MAST config dict
    cc = get_configuration('imviz')
    cc['settings']['viewer_spec'] = cc['settings'].get('configuration', 'default')
    cc['settings']['configuration'] = 'mastviz'
    cc['settings']['visible'] = {'menu_bar': False, 'toolbar': False, 'tray': False,
                                 'tab_headers': False}
    cc['toolbar'].remove('g-data-tools') if cc['toolbar'].count('g-data-tools') else None
    cc['toolbar'].remove('g-viewer-creator') if cc['toolbar'].count('g-viewer-creator') else None
    cc['toolbar'].remove('g-image-viewer-creator') if cc['toolbar'].count('g-image-viewer-creator') else None  # noqa

    app = PrivateApplication(cc)
    im = Imviz(app)
    im.load_data(np.ones((2, 2)), data_label='my_array')

    assert im._app.get_viewer_ids() == ['mastviz-0']
    assert im._app.data_collection[0].shape == (2, 2)


def test_zoom_center_radius_init(deconfigged_helper):
    """Regression test for https://github.com/spacetelescope/jdaviz/issues/3217"""
    arr = np.ones((10, 10))
    deconfigged_helper.load(arr, data_label='my_array', format='Image')
    viewer = deconfigged_helper.viewers['Image']

    assert viewer._obj.glue_viewer.state.zoom_center_x > 0
    assert viewer._obj.glue_viewer.state.zoom_center_y > 0
    assert viewer._obj.glue_viewer.state.zoom_radius > 0


def test_catalog_in_image_viewer(deconfigged_helper, image_2d_wcs,
                                 sky_coord_only_source_catalog):
    data = NDData(np.ones((128, 128)) * u.nJy, wcs=image_2d_wcs)
    deconfigged_helper.load(data, data_label='my_data', format='Image')

    # change alignment to WCS to enable catalog visibility
    deconfigged_helper.plugins['Orientation'].align_by = 'WCS'

    # Load the source catalog into the data collection, and into the image viewer
    deconfigged_helper.load(sky_coord_only_source_catalog, format='Catalog',
                            data_label='my_catalog')

    iv = deconfigged_helper.viewers['Image']
    dm = iv.data_menu
    po = deconfigged_helper.plugins['Plot Options']

    # both image and catalog should be in the data menu, able to be
    # loaded/removed from the image viewer
    assert dm.data_labels_visible == ['my_catalog', 'my_data[DATA]']

    assert deconfigged_helper._app.data_collection[2].label == 'my_catalog'
    assert deconfigged_helper._app.data_collection[2].meta.get('_importer') == 'CatalogImporter'

    # since catalog is already loaded, it should not be in the "available"
    # choices, but should be in the visible list
    assert 'my_catalog' not in dm._obj.dataset.choices
    assert 'my_catalog' in dm.data_labels_visible

    # should be available from plot options
    assert 'my_catalog' in po.layer.choices

    # test that mouseover appears
    mo = deconfigged_helper._coords_info
    assert mo.dataset.selected == 'auto'
    assert 'my_catalog' in mo.dataset.choices

    mo._viewer_mouse_event(iv._obj.glue_viewer,
                           {'event': 'mousemove', 'domain': {'x': 0.5, 'y': 0.5}})
    assert mo.as_dict()['data_label'] == 'my_data[DATA]'

    mo.dataset.selected = 'my_catalog'
    mo._viewer_mouse_event(iv._obj.glue_viewer,
                           {'event': 'mousemove', 'domain': {'x': 0.5, 'y': 0.5}})
    assert mo.as_dict()['data_label'] == 'my_catalog'
    assert mo.as_text()[0] == 'Source ID 2'
    assert mo.as_text()[1] == 'World 22h30m06.8256s -20d49m37.4520s (ICRS)'
    # some floating point discrepancies in degs is acceptable, WCS tested elsewhere
    assert len(mo.as_text()[2]) > 0

    # changing to pixel linking should set the layer to hidden
    # and remove from the plot options layer tabs
    deconfigged_helper.plugins['Orientation'].align_by = 'Pixels'
    assert 'my_catalog' not in dm.data_labels_visible
    assert 'my_catalog' not in po.layer.choices

    # test loading/removing another image dataset, which involves linking
    deconfigged_helper.load(data, data_label='my_data_2', format='Image')
    dm.layer.selected = ['my_data_2[DATA]']
    dm.remove_from_app()

    # test sucessfully removing the catalog
    dm.layer.selected = ['my_catalog']
    dm.remove_from_app()
    assert 'my_catalog' not in deconfigged_helper._app.data_collection.labels


def test_get_viewport_sky_region_wcs(deconfigged_helper, image_hdu_wcs):
    deconfigged_helper.load(image_hdu_wcs, data_label='image_hdu_wcs', format='Image')
    viewer = deconfigged_helper.viewers['Image']
    region = viewer.get_viewport_region()

    expected_vertices = SkyCoord(
        [337.52124634, 337.52124633, 337.51664042, 337.51664038],
        [-20.83297927, -20.83118685, -20.83118681, -20.83297923],
        unit=u.deg
    )

    assert_allclose(
        region.vertices.separation(expected_vertices).arcsec,
        0, atol=5
    )


def test_get_viewport_sky_region_gwcs(deconfigged_helper):
    shape = (10, 10)
    data = np.ones(shape)
    ndd = NDData(data=data, wcs=create_example_gwcs(shape))

    deconfigged_helper.load(ndd, data_label='ndd', format='Image')
    viewer = deconfigged_helper.viewers['Image']
    region = viewer.get_viewport_region()

    expected_vertices = SkyCoord(
        [197.89244966, 197.89271435, 197.89256153, 197.89229684],
        [-1.36574339, -1.36559061, -1.36532599, -1.36547877],
        unit=u.deg
    )

    assert_allclose(
        region.vertices.separation(expected_vertices).arcsec,
        0, atol=5
    )


def test_get_viewport_sky_no_wcs(deconfigged_helper):
    shape = (10, 10)
    data = np.ones(shape)
    ndd = NDData(data=data)

    deconfigged_helper.load(ndd, data_label='ndd', format='Image')
    viewer = deconfigged_helper.viewers['Image']

    with pytest.warns(UserWarning, match="does not have valid WCS"):
        viewer.get_viewport_region()


def test_get_viewport_pixel_region(deconfigged_helper):
    shape = (10, 10)
    data = np.ones(shape)
    ndd = NDData(data=data, wcs=create_example_gwcs(shape))

    deconfigged_helper.load(ndd, data_label='ndd', format='Image')
    viewer = deconfigged_helper.viewers['Image']

    data_label = deconfigged_helper._app.data_collection[0].label
    region = viewer.get_viewport_region('pixel', data_label)
    assert_allclose(
        region.vertices.x, [-0.5, -0.5, 9.5, 9.5]
    )
    assert_allclose(
        region.vertices.y, [-0.5, 9.5, 9.5, -0.5]
    )


def test_get_viewport_pixel_region_bad_label(deconfigged_helper):
    shape = (10, 10)
    data = np.ones(shape)
    ndd = NDData(data=data)
    deconfigged_helper.load(ndd, data_label='label 1', format='Image')

    with pytest.raises(ValueError, match="No data found with label xyz"):
        viewer = deconfigged_helper.viewers['Image']
        viewer.get_viewport_region('pixel', 'xyz')


def test_get_viewport_pixel_region_no_label(deconfigged_helper):
    shape = (10, 10)
    data = np.ones(shape)
    ndd = NDData(data=data)
    deconfigged_helper.load(ndd, data_label='label 1', format='Image')

    with pytest.raises(ValueError,
                       match="`get_viewport_region` requires a data label"):
        viewer = deconfigged_helper.viewers['Image']
        viewer.get_viewport_region('pixel')


class TestDeleteData(BaseImviz_WCS_NoWCS):

    def test_plot_options_after_destroy(self):
        self.imviz.create_image_viewer(viewer_name="imviz-1")
        self.imviz._app.add_data_to_viewer('imviz-1', 'no_wcs[SCI,1]')

        po = self.imviz.plugins['Plot Options']
        po.open_in_tray()
        po.viewer = "imviz-1"
        po.stretch_function = "Square Root"
        self.imviz.destroy_viewer("imviz-1")
        assert len(po.layer.choices) == 2


class TestRegionOverlay:
    @pytest.fixture(autouse=True)
    def setup_class(self, deconfigged_helper):
        np.random.seed(42)
        # Data with WCS
        hdu_wcs = _image_hdu_wcs(arr=np.arange(100).reshape((10, 10)))
        deconfigged_helper.load(hdu_wcs, data_label='ndd', format='Image')

        self.imviz = deconfigged_helper
        self.viewer = deconfigged_helper.viewers['Image']._obj.glue_viewer

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (100, 100)
        self.viewer.state._set_axes_aspect_ratio(1)

        # create polygon sky regions near the image viewer's sky position:
        ra = np.array([337.51928678, 337.51928679, 337.51697352, 337.5169735])
        dec = np.array([-20.83245874, -20.83160296, -20.83160294, -20.83245871])

        self.regions = []
        self.region_labels = []
        for i in range(5):
            scatter_deg = 2e-4
            ra_offset = np.random.uniform(-scatter_deg, scatter_deg, size=ra.size)
            dec_offset = np.random.uniform(-scatter_deg, scatter_deg, size=ra.size)
            vertices = SkyCoord(ra + ra_offset, dec + dec_offset, unit='deg')
            self.regions.append(PolygonSkyRegion(vertices))
            self.region_labels.append(i)

    def test_add_remove_region_overlay(self):

        self.viewer._add_region_overlay(
            region=self.regions,
            region_label=self.region_labels,
            selected=False
        )

        region_overlay_marks = [
            mark for mark in self.viewer.figure.marks
            if isinstance(mark, RegionOverlay)
        ]

        # check that marks were added:
        n_marks_added = len(region_overlay_marks)
        n_marks_expected = len(self.region_labels)
        assert n_marks_added == n_marks_expected
        assert not any(mark.selected for mark in region_overlay_marks)

        labels_found = [mark.label for mark in region_overlay_marks]
        assert self.region_labels == labels_found

        # remove a region:
        self.viewer._remove_region_overlay(3)
        assert len([
            mark for mark in self.viewer.figure.marks
            if isinstance(mark, RegionOverlay)
        ]) == n_marks_added - 1

        # remove all regions:
        self.viewer._remove_all_region_overlays()
        assert not len([
            mark for mark in self.viewer.figure.marks
            if isinstance(mark, RegionOverlay)
        ])

    def test_select_region_overlay(self):
        self.viewer._add_region_overlay(
            region=self.regions,
            region_label=self.region_labels,
            selected=False
        )

        select_labels_expected = [0, 1]
        self.viewer._select_region_overlay(
            region_label=select_labels_expected
        )

        region_overlay_marks = [
            mark for mark in self.viewer.figure.marks
            if isinstance(mark, RegionOverlay)
        ]

        # check selected status is correct
        for mark in region_overlay_marks:
            if mark.label in select_labels_expected:
                assert mark.selected
            else:
                assert not mark.selected

        # check that selected regions appear at the end of the
        # marks list, so they're plotted on top of the not-selected marks
        assert select_labels_expected == [mark.label for mark in region_overlay_marks[-2:]]
        assert [2, 3, 4] == [mark.label for mark in region_overlay_marks[:-2]]

        selected_marks = [
            mark for mark in region_overlay_marks if mark.selected
        ]
        not_selected_marks = [
            mark for mark in region_overlay_marks if not mark.selected
        ]

        # check that correct marks are selected
        selected_labels_found = [mark.label for mark in selected_marks]
        assert select_labels_expected == selected_labels_found

        # check that selected and not-selected marks have
        # the expected styles:
        check_selected_attrs = ['stroke_width', 'colors']

        for attr in check_selected_attrs:
            for mark in selected_marks:
                assert getattr(mark, attr) == mark.selected_style[attr]

            for mark in not_selected_marks:
                assert getattr(mark, attr) == mark.default_style[attr]

        # test select all
        self.viewer._select_all_region_overlays()
        n_selected = len([
            mark for mark in self.viewer.figure.marks if mark.selected
        ])
        assert n_selected == len(self.regions)

    def test_deselect_region_overlay(self):
        # all selected
        self.viewer._add_region_overlay(
            region=self.regions,
            region_label=self.region_labels,
            selected=True
        )

        deselect_labels = [0, 3, 4]
        select_labels_expected = [1, 2]
        self.viewer._deselect_region_overlay(
            region_label=deselect_labels
        )

        region_overlay_marks = [
            mark for mark in self.viewer.figure.marks
            if isinstance(mark, RegionOverlay)
        ]

        selected_marks = [
            mark for mark in region_overlay_marks if mark.selected
        ]

        # check that correct marks are selected
        selected_labels_found = [mark.label for mark in selected_marks]
        assert select_labels_expected == selected_labels_found

        # deselect all, check none are selected
        self.viewer._deselect_all_region_overlays()
        assert not len([
            mark for mark in self.viewer.figure.marks
            if isinstance(mark, RegionOverlay) and mark.selected
        ])
