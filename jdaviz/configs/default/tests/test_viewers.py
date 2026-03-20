"""
Tests for JdavizViewerMixin ROI edit-detection helpers and the
``apply_roi`` override that lets users resize/move subsets in-place
in the deconfigged configuration.
"""

import numpy as np
import pytest
from astropy.nddata import NDData
from glue.core.edit_subset_mode import NewMode
from glue.core.roi import (
    CircularAnnulusROI,
    CircularROI,
    EllipticalROI,
    RectangularROI,
    XRangeROI,
)
from glue_jupyter.bqplot.common.tools import TrueCircularROI

from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin

_M = JdavizViewerMixin


# ---------------------------------------------------------------------------
# _is_circular_edit
# ---------------------------------------------------------------------------

class TestIsCircularEdit:
    """
    Tests for ``JdavizViewerMixin._is_circular_edit``.
    """

    def test_resize_same_center(self):
        old = CircularROI(xc=10, yc=10, radius=5)
        new = CircularROI(xc=10, yc=10, radius=8)
        assert _M._is_circular_edit(old, new)

    def test_resize_center_within_radius(self):
        old = CircularROI(xc=10, yc=10, radius=5)
        new = CircularROI(xc=12, yc=10, radius=8)
        assert _M._is_circular_edit(old, new)

    def test_move_same_radius(self):
        old = CircularROI(xc=10, yc=10, radius=5)
        new = CircularROI(xc=50, yc=50, radius=5)
        assert _M._is_circular_edit(old, new)

    def test_new_draw(self):
        old = CircularROI(xc=10, yc=10, radius=5)
        new = CircularROI(xc=50, yc=50, radius=12)
        assert not _M._is_circular_edit(old, new)

    def test_zero_radius(self):
        old = CircularROI(xc=10, yc=10, radius=0)
        new = CircularROI(xc=10, yc=10, radius=5)
        assert not _M._is_circular_edit(old, new)


# ---------------------------------------------------------------------------
# _is_annulus_edit
# ---------------------------------------------------------------------------

class TestIsAnnulusEdit:
    """
    Tests for ``JdavizViewerMixin._is_annulus_edit``.
    """

    def test_resize_same_center(self):
        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=3, outer_radius=6)
        new = CircularAnnulusROI(xc=10, yc=10, inner_radius=4, outer_radius=8)
        assert _M._is_annulus_edit(old, new)

    def test_move_same_radii(self):
        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=3, outer_radius=6)
        new = CircularAnnulusROI(xc=50, yc=50, inner_radius=3, outer_radius=6)
        assert _M._is_annulus_edit(old, new)

    def test_new_draw(self):
        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=3, outer_radius=6)
        new = CircularAnnulusROI(xc=50, yc=50, inner_radius=5, outer_radius=10)
        assert not _M._is_annulus_edit(old, new)

    def test_different_inner_only(self):
        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=3, outer_radius=6)
        new = CircularAnnulusROI(xc=50, yc=50, inner_radius=4, outer_radius=6)
        assert not _M._is_annulus_edit(old, new)

    def test_zero_outer_radius(self):
        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=0, outer_radius=0)
        new = CircularAnnulusROI(xc=10, yc=10, inner_radius=2, outer_radius=5)
        assert not _M._is_annulus_edit(old, new)


# ---------------------------------------------------------------------------
# _is_elliptical_edit
# ---------------------------------------------------------------------------

class TestIsEllipticalEdit:
    """
    Tests for ``JdavizViewerMixin._is_elliptical_edit``.
    """

    def test_resize_same_center(self):
        old = EllipticalROI(xc=10, yc=10, radius_x=5, radius_y=3)
        new = EllipticalROI(xc=10, yc=10, radius_x=8, radius_y=6)
        assert _M._is_elliptical_edit(old, new)

    def test_move_same_radii(self):
        old = EllipticalROI(xc=10, yc=10, radius_x=5, radius_y=3)
        new = EllipticalROI(xc=50, yc=50, radius_x=5, radius_y=3)
        assert _M._is_elliptical_edit(old, new)

    def test_new_draw(self):
        old = EllipticalROI(xc=10, yc=10, radius_x=5, radius_y=3)
        new = EllipticalROI(xc=50, yc=50, radius_x=8, radius_y=6)
        assert not _M._is_elliptical_edit(old, new)


# ---------------------------------------------------------------------------
# _is_rectangular_edit
# ---------------------------------------------------------------------------

class TestIsRectangularEdit:
    """
    Tests for ``JdavizViewerMixin._is_rectangular_edit``.
    """

    def test_resize_same_center(self):
        old = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        new = RectangularROI(xmin=-2, xmax=12, ymin=-2, ymax=12)
        assert _M._is_rectangular_edit(old, new)

    def test_move_same_size(self):
        old = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        new = RectangularROI(xmin=50, xmax=60, ymin=50, ymax=60)
        assert _M._is_rectangular_edit(old, new)

    def test_new_draw(self):
        old = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        new = RectangularROI(xmin=50, xmax=80, ymin=50, ymax=80)
        assert not _M._is_rectangular_edit(old, new)


# ---------------------------------------------------------------------------
# _is_roi_edit  (dispatcher)
# ---------------------------------------------------------------------------

class TestIsRoiEdit:
    """
    Tests for the ``_is_roi_edit`` dispatch method.
    """

    def test_dispatches_circular(self):
        old = CircularROI(xc=10, yc=10, radius=5)
        new = CircularROI(xc=10, yc=10, radius=8)
        assert _M._is_roi_edit(_M, old, new)

    def test_dispatches_true_circular(self):
        old = TrueCircularROI(xc=10, yc=10, radius=5)
        new = TrueCircularROI(xc=10, yc=10, radius=8)
        assert _M._is_roi_edit(_M, old, new)

    def test_dispatches_true_circular_move(self):
        old = TrueCircularROI(xc=10, yc=10, radius=5)
        new = TrueCircularROI(xc=50, yc=50, radius=5)
        assert _M._is_roi_edit(_M, old, new)

    def test_dispatches_annulus(self):
        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=3, outer_radius=6)
        new = CircularAnnulusROI(xc=10, yc=10, inner_radius=4, outer_radius=8)
        assert _M._is_roi_edit(_M, old, new)

    def test_dispatches_elliptical(self):
        old = EllipticalROI(xc=10, yc=10, radius_x=5, radius_y=3)
        new = EllipticalROI(xc=50, yc=50, radius_x=5, radius_y=3)
        assert _M._is_roi_edit(_M, old, new)

    def test_dispatches_rectangular(self):
        old = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        new = RectangularROI(xmin=50, xmax=60, ymin=50, ymax=60)
        assert _M._is_roi_edit(_M, old, new)

    def test_different_types_returns_false(self):
        old = CircularROI(xc=10, yc=10, radius=5)
        new = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        assert not _M._is_roi_edit(_M, old, new)

    def test_unsupported_type_returns_false(self):
        assert not _M._is_roi_edit(_M, object(), object())


# ---------------------------------------------------------------------------
# _is_range_edit
# ---------------------------------------------------------------------------

class TestIsRangeEdit:
    """
    Tests for ``JdavizViewerMixin._is_range_edit``.
    """

    @pytest.fixture()
    def _make_state(self):
        from glue.core.subset import RangeSubsetState
        return RangeSubsetState(lo=10, hi=20)

    def test_resize_midpoint_inside(self, _make_state):
        roi = XRangeROI(12, 22)
        assert _M._is_range_edit(roi, _make_state)

    def test_move_same_width(self, _make_state):
        roi = XRangeROI(25, 35)
        assert _M._is_range_edit(roi, _make_state)

    def test_new_draw(self, _make_state):
        roi = XRangeROI(50, 80)
        assert not _M._is_range_edit(roi, _make_state)

    def test_no_min_max_attributes(self, _make_state):
        assert not _M._is_range_edit(object(), _make_state)


# ---------------------------------------------------------------------------
# Programmatic test: apply_roi in deconfigged
# ---------------------------------------------------------------------------

class TestDeconfiggedSubsetEditInPlace:
    """
    End-to-end test verifying that resize and move operations in
    deconfigged modify subsets in-place, while new draws create
    new subsets.
    """

    @pytest.fixture(autouse=True)
    def setup_method(self, deconfigged_helper, image_2d_wcs):
        """
        Set up deconfigged app with a 100x100 image.
        """
        arr = np.ones((100, 100))
        ndd = NDData(arr, wcs=image_2d_wcs)
        deconfigged_helper.load(ndd, data_label='test_image')
        self.app = deconfigged_helper
        self.viewer = list(
            deconfigged_helper.app.get_viewers_of_cls('ImvizImageView')
        )[0]

    def _subset_count(self):
        return len(self.app.app.data_collection.subset_groups)

    def _active_subset_state(self):
        esm = self.viewer.session.edit_subset_mode
        if esm.edit_subset:
            return esm.edit_subset[0].subset_state
        return None

    def test_draw_creates_new_subset(self):
        """
        Drawing a circle should create a new subset.
        """
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=10))
        assert self._subset_count() == 1

    def test_resize_modifies_in_place(self):
        """
        Resizing (same center, different radius) should modify
        the existing subset rather than creating a second one.
        """
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=15))
        assert self._subset_count() == 1
        assert np.isclose(self._active_subset_state().roi.radius, 15)

    def test_move_modifies_in_place(self):
        """
        Moving (same radius, different center) should modify
        the existing subset rather than creating a second one.
        """
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(CircularROI(xc=60, yc=55, radius=10))
        assert self._subset_count() == 1
        assert np.isclose(self._active_subset_state().roi.xc, 60)

    def test_new_draw_elsewhere_creates_second_subset(self):
        """
        Drawing a differently sized region far away should create
        a new subset, not modify the existing one.
        """
        self.viewer.apply_roi(CircularROI(xc=20, yc=20, radius=5))
        self.viewer.apply_roi(CircularROI(xc=80, yc=80, radius=12))
        assert self._subset_count() == 2

    def test_annulus_resize_in_place(self):
        """
        Resizing an annulus should modify it in-place (regression
        for the center-in-hole bug).
        """
        self.viewer.apply_roi(
            CircularAnnulusROI(xc=50, yc=50, inner_radius=5, outer_radius=10)
        )
        self.viewer.apply_roi(
            CircularAnnulusROI(xc=50, yc=50, inner_radius=7, outer_radius=14)
        )
        assert self._subset_count() == 1

    def test_annulus_move_in_place(self):
        """
        Moving an annulus should modify it in-place.
        """
        self.viewer.apply_roi(
            CircularAnnulusROI(xc=50, yc=50, inner_radius=5, outer_radius=10)
        )
        self.viewer.apply_roi(
            CircularAnnulusROI(xc=60, yc=55, inner_radius=5, outer_radius=10)
        )
        assert self._subset_count() == 1

    def test_rectangle_resize_in_place(self):
        """
        Resizing a rectangle should modify it in-place.
        """
        self.viewer.apply_roi(RectangularROI(xmin=40, xmax=60, ymin=40, ymax=60))
        self.viewer.apply_roi(RectangularROI(xmin=35, xmax=65, ymin=35, ymax=65))
        assert self._subset_count() == 1

    def test_rectangle_move_in_place(self):
        """
        Moving a rectangle should modify it in-place.
        """
        self.viewer.apply_roi(RectangularROI(xmin=40, xmax=60, ymin=40, ymax=60))
        self.viewer.apply_roi(RectangularROI(xmin=50, xmax=70, ymin=50, ymax=70))
        assert self._subset_count() == 1

    def test_mode_restored_after_override(self):
        """
        After an in-place edit the mode should remain NewMode so
        that subsequent new draws still create new subsets.
        """
        esm = self.viewer.session.edit_subset_mode
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=15))
        assert esm.mode is NewMode

    def test_multiple_subsets_then_edit(self):
        """
        Create two subsets, then resize the second; only the
        second should be modified.
        """
        self.viewer.apply_roi(CircularROI(xc=20, yc=20, radius=5))
        self.viewer.apply_roi(CircularROI(xc=80, yc=80, radius=12))
        assert self._subset_count() == 2
        self.viewer.apply_roi(CircularROI(xc=80, yc=80, radius=18))
        assert self._subset_count() == 2

    def test_true_circular_resize_in_place(self):
        """
        TrueCircularROI (from bqplot:truecircle) should resize
        in-place just like CircularROI.
        """
        self.viewer.apply_roi(TrueCircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(TrueCircularROI(xc=50, yc=50, radius=15))
        assert self._subset_count() == 1
        assert np.isclose(self._active_subset_state().roi.radius, 15)

    def test_true_circular_move_in_place(self):
        """
        TrueCircularROI (from bqplot:truecircle) should move
        in-place just like CircularROI.
        """
        self.viewer.apply_roi(TrueCircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(TrueCircularROI(xc=60, yc=55, radius=10))
        assert self._subset_count() == 1
        assert np.isclose(self._active_subset_state().roi.xc, 60)
