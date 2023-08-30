import os

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import NoConvergence
from echo import delay_callback
from glue.config import colormaps
from regions import Regions

from jdaviz.configs.imviz.helper import get_top_layer_index
from jdaviz.core.events import SnackbarMessage, MarkersChangedMessage
from jdaviz.core.helpers import data_has_valid_wcs

__all__ = ['AstrowidgetsImageViewerMixin']


class AstrowidgetsImageViewerMixin:
    """This class implements ``astrowidgets`` API for Jdaviz *image* viewer.
    This does not provide a fully functional viewer, but rather
    should be used as mixin into an existing viewer subclass.

    A child class that uses this must run :meth:`init_astrowidgets_api`
    within its ``__init__``.

    .. note:: Do not use this for spectral or cube viewers.

    """
    RESERVED_MARKER_SET_NAMES = ['all']

    # __init__ not called, so use this to setup.
    def init_astrowidgets_api(self):
        """This method must be called in child class ``__init__``."""
        # Markers
        self._marker_regions = {}  # defaultdict + Regions combo does not work
        self._default_mark_tag_name = 'default-marker-name'
        self.marker = {'color': 'red', 'alpha': 1.0}

    def save(self, filename):
        """Save out the current image view to given PNG filename.

        Parameters
        ----------
        filename : str
            PNG filename. If the given file already exists, it will be
            silently overwritten.

        """
        if not filename.lower().endswith('.png'):
            filename = filename + '.png'

        # https://github.com/bqplot/bqplot/pull/1397
        def on_png_received(data):
            with open(os.path.expanduser(filename), 'bw') as f:
                f.write(data)

        self.figure.get_png_data(on_png_received)

    def center_on(self, point):
        """Centers the view on a particular point on the top visible layer.
        The data label of the top visible layer can be queried using the viewer's
        `~jdaviz.configs.imviz.plugins.viewers.ImvizImageView.top_visible_data_label`
        property.

        Parameters
        ----------
        point : tuple or `~astropy.coordinates.SkyCoord`
            If tuple of ``(X, Y)`` is given, it is assumed
            to be in data coordinates and 0-indexed.

        Raises
        ------
        AttributeError
            Sky coordinates are given but image does not have a valid WCS.

        """
        i_top = get_top_layer_index(self)
        image = self.layers[i_top].layer

        if isinstance(point, SkyCoord):
            if data_has_valid_wcs(image):
                try:
                    point = image.coords.world_to_pixel(point)  # 0-indexed X, Y
                except NoConvergence as e:  # pragma: no cover
                    self.session.hub.broadcast(SnackbarMessage(
                        f'{point} is likely out of bounds: {repr(e)}',
                        color="warning", sender=self))
                    return
            else:
                raise AttributeError(f'{getattr(image, "label", None)} does not have a valid WCS')

        if not np.all(np.isfinite(point)):
            return
        elif hasattr(self, '_get_real_xy'):
            # User gives pixel wrt top layer but we want reference data location.
            pix = self._get_real_xy(image, point[0], point[1], reverse=True)
        else:  # pragma: no cover
            pix = point

        width = self.state.x_max - self.state.x_min
        height = self.state.y_max - self.state.y_min

        with delay_callback(self.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            self.state.x_min = pix[0] - (width * 0.5)
            self.state.y_min = pix[1] - (height * 0.5)
            self.state.x_max = self.state.x_min + width
            self.state.y_max = self.state.y_min + height

    def offset_by(self, dx, dy):
        """Move the center to a point that is given offset
        away from the current center.

        Parameters
        ----------
        dx, dy : float or `~astropy.units.Quantity`
            Offset value. Without a unit, assumed to be pixel offsets.
            If a unit is attached, offset by pixel or sky is assumed from
            the unit.

        Raises
        ------
        AttributeError
            Sky offset is given but image does not have a valid WCS.

        ValueError
            Offsets are of different types.

        astropy.units.core.UnitTypeError
            Sky offset has invalid unit.

        """
        width = self.state.x_max - self.state.x_min
        height = self.state.y_max - self.state.y_min

        dx, dx_coord = _offset_is_pixel_or_sky(dx)
        dy, dy_coord = _offset_is_pixel_or_sky(dy)

        if dx_coord != dy_coord:
            raise ValueError(f'dx is of type {dx_coord} but dy is of type {dy_coord}')

        if dx_coord == 'wcs':
            i_top = get_top_layer_index(self)
            image = self.layers[i_top].layer
            if data_has_valid_wcs(image):
                # To avoid distortion headache, assume offset is relative to
                # displayed center.
                x_cen = self.state.x_min + (width * 0.5)
                y_cen = self.state.y_min + (height * 0.5)
                sky_cen = image.coords.pixel_to_world(x_cen, y_cen)
                new_sky_cen = sky_cen.spherical_offsets_by(dx, dy)
                self.center_on(new_sky_cen)
            else:
                raise AttributeError(f'{getattr(image, "label", None)} does not have a valid WCS')
        else:
            with delay_callback(self.state, 'x_min', 'x_max', 'y_min', 'y_max'):
                self.state.x_min += dx
                self.state.y_min += dy
                self.state.x_max = self.state.x_min + width
                self.state.y_max = self.state.y_min + height

    @property
    def zoom_level(self):
        """Zoom level:

        * 1 means real-pixel-size.
        * 2 means zoomed in by a factor of 2.
        * 0.5 means zoomed out by a factor of 2.
        * 'fit' means zoomed to fit the whole image width into display.

        """
        if self.shape is None:  # pragma: no cover
            raise ValueError('Viewer is still loading, try again later')

        screenx = self.shape[1]
        screeny = self.shape[0]
        zoom_x = screenx / (self.state.x_max - self.state.x_min)
        zoom_y = screeny / (self.state.y_max - self.state.y_min)

        return max(zoom_x, zoom_y)  # Similar to Ginga get_scale()

    # Loosely based on glue/viewers/image/state.py
    @zoom_level.setter
    def zoom_level(self, val):
        if ((not isinstance(val, (int, float)) and val != 'fit') or
                (isinstance(val, (int, float)) and val <= 0)):
            raise ValueError(f'Unsupported zoom level: {val}')

        image = self.state.reference_data
        if (image is None or self.shape is None or
                self.state.x_att is None or self.state.y_att is None):  # pragma: no cover
            return

        # Zoom on X and Y will auto-adjust.
        if val == 'fit':
            self.state.reset_limits()
            return
        else:
            cur_xcen = (self.state.x_min + self.state.x_max) * 0.5
            new_dx = self.shape[1] * 0.5 / val
            new_x_min = cur_xcen - new_dx
            new_x_max = cur_xcen + new_dx

        with delay_callback(self.state, 'x_min', 'x_max'):
            self.state.x_min = new_x_min - 0.5
            self.state.x_max = new_x_max - 0.5

        # We need to adjust the limits in here to avoid triggering all
        # the update events then changing the limits again.
        self.state._adjust_limits_aspect()

    # Discussion on why we need two different ways to set zoom at
    # https://github.com/astropy/astrowidgets/issues/144
    def zoom(self, val):
        """Zoom in or out by the given factor.

        Parameters
        ----------
        val : int or float
            The zoom level to zoom the image.
            See `zoom_level`.

        Raises
        ------
        ValueError
            Invalid zoom factor.

        """
        if not isinstance(val, (int, float)):
            raise ValueError(f"zoom only accepts int or float but got '{val}'")
        self.zoom_level = self.zoom_level * val

    @property
    def colormap_options(self):
        """List of colormap names."""
        # Do not sort to match Plot Options order.
        return [member[0] for member in colormaps.members]

    def set_colormap(self, cmap):
        """Set colormap to the given colormap name.

        Parameters
        ----------
        cmap : str
            Colormap name. Possible values can be obtained from
            :meth:`colormap_options`.

        Raises
        ------
        ValueError
            Invalid colormap name.

        """
        cm = None
        for member in colormaps.members:
            if member[0] == cmap:
                cm = member[1]
                break

        if cm is None:
            raise ValueError(f"Invalid colormap '{cmap}', must be one of {self.colormap_options}")

        i_top = get_top_layer_index(self)
        self.state.layers[i_top].cmap = cm

    @property
    def stretch_options(self):
        """List of all available options for image stretching.

        Their ``astropy.visualization`` counterparts are also accepted, as follows:

        * ``'arcsinh'``: ``astropy.visualization.AsinhStretch``
        * ``'linear'``: ``astropy.visualization.LinearStretch``
        * ``'log'``: ``astropy.visualization.LogStretch``
        * ``'sqrt'``: ``astropy.visualization.SqrtStretch``

        """
        # TODO: Is there a better way to access this in Glue? See glue/viewers/image/state.py
        return ['arcsinh', 'linear', 'log', 'sqrt']

    @property
    def stretch(self):
        """The image stretching algorithm in use."""
        i_top = get_top_layer_index(self)
        return self.state.layers[i_top].stretch

    @stretch.setter
    def stretch(self, val):
        valid_vals = self.stretch_options

        if isinstance(val, type):  # is a class
            # Translate astropy.visualization
            from astropy.visualization import AsinhStretch, LinearStretch, LogStretch, SqrtStretch
            if issubclass(val, AsinhStretch):
                val = 'arcsinh'
            elif issubclass(val, LinearStretch):
                val = 'linear'
            elif issubclass(val, LogStretch):
                val = 'log'
            elif issubclass(val, SqrtStretch):
                val = 'sqrt'
            else:
                raise ValueError(f"Invalid stretch {val}, must be one of {valid_vals}")
        elif val not in valid_vals:
            raise ValueError(f"Invalid stretch '{val}', must be one of {valid_vals}")

        i_top = get_top_layer_index(self)
        self.state.layers[i_top].stretch = val

    @property
    def autocut_options(self):
        """List of all available options for automatic image cut levels."""
        # See glue-jupyter/bqplot/image/state.py#L29
        return ['minmax', '99.5%', '99%', '95%', '90%']

    @property
    def cuts(self):
        """Current image cut levels.

        To set new cut levels, either provide a tuple of ``(low, high)`` values
        or one of the options from `autocut_options`.

        """
        i_top = get_top_layer_index(self)
        return self.state.layers[i_top].v_min, self.state.layers[i_top].v_max

    # TODO: Support astropy.visualization, see https://github.com/glue-viz/glue/issues/2218
    @cuts.setter
    def cuts(self, val):
        i_top = get_top_layer_index(self)

        if isinstance(val, str):  # autocut
            if val == 'minmax':
                val = 100
            elif val == '99.5%':
                val = 99.5
            elif val == '99%':
                val = 99
            elif val == '95%':
                val = 95
            elif val == '90%':
                val = 90
            else:
                raise ValueError(f"Invalid autocut '{val}', must be one of {self.autocut_options}")
            self.state.layers[i_top].percentile = val
        else:  # (low, high)
            if (not isinstance(val, (list, tuple)) or len(val) != 2
                    or not np.all([isinstance(x, (int, float)) for x in val])):
                raise ValueError(f"Invalid cut levels {val}, must be (low, high)")
            self.state.layers[i_top].v_min = val[0]
            self.state.layers[i_top].v_max = val[1]

    @property
    def marker(self):
        """Marker to use.

        Marker can be set as follows; e.g.::

            {'color': 'red', 'alpha': 1.0}
            {'color': '#ff0000', 'alpha': 0.5}
            {'color': (1, 0, 0), 'fill': False}

        The valid properties for Glue markers are listed at
        https://docs.glueviz.org/en/stable/api/glue.core.visual.VisualAttributes.html

        """
        return self._marker_dict

    @marker.setter
    def marker(self, val):
        # NOTE: markersize is controled by Region dimension.
        # Validation: Ideally Glue should do this but we have to due to
        # https://github.com/glue-viz/glue/issues/2203
        given = set(val.keys())
        allowed = set(('color', 'alpha', 'fill'))
        if not given.issubset(allowed):
            raise KeyError(f'Invalid attribute(s): {given - allowed}')
        if 'color' in val:
            from matplotlib.colors import ColorConverter
            ColorConverter().to_rgb(val['color'])  # ValueError: Invalid RGBA argument
        if 'alpha' in val:
            alpha = val['alpha']
            if not isinstance(alpha, (int, float)) or alpha < 0 or alpha > 1:
                raise ValueError(f'Invalid alpha: {alpha}')
        if 'fill' in val:
            fill = val['fill']
            if not isinstance(fill, bool):
                raise ValueError(f'Invalid fill: {fill}')

        # Only set this once we have successfully validated a marker.
        # Those not set here use Glue defaults.
        self._marker_dict = val

    def _validate_marker_name(self, marker_name):
        """Raise an error if the marker_name is not allowed."""
        if marker_name in self.RESERVED_MARKER_SET_NAMES:
            raise ValueError(
                f"The marker name {marker_name} is not allowed. Any name is "
                f"allowed except these: {', '.join(self.RESERVED_MARKER_SET_NAMES)}")

    def get_markers(self, marker_name=None):
        """Get the markers as regions.

        Parameters
        ----------
        marker_name : str or `None`
            The name of the marker set to use. If `None`, all
            markers will be returned.

        Returns
        -------
        regs : `regions.Regions`
            Regions object with all the desired regions.
            If `None` is given, it may contain an empty list.

        Raises
        ------
        KeyError
            Given ``marker_name`` does not exist.

        """
        if marker_name is None:
            regs = Regions([])
            # Should we prune duplicates? Would set() work?
            for val in self._marker_regions.values():
                regs.extend(val.regions)
        else:
            regs = self._marker_regions[marker_name]
        return regs

    def add_markers(self, regions, marker_name=None):
        """Creates markers using given Astropy regions.

        .. note:: Marker appearance is controlled by region shape and ``self.marker``.

        .. note::
           Once markers are added, they are static. To change markers,
           remove and then re-add the modified regions manually.

        Parameters
        ----------
        regions : `regions.Regions` or a list of `regions.Region`
            Astropy regions to mark.

        marker_name : str, optional
            Name to assign the markers. Providing a name
            allows markers to be removed by name at a later time.

        Raises
        ------
        TypeError
            Invalid regions.

        ValueError
            Invalid marker name.

        """
        raise NotImplementedError  # FIXME

        if isinstance(regions, list):
            regions = Regions(regions)  # Delegate any further checks to Regions
        elif not isinstance(regions, Regions):
            raise TypeError(f"Markers cannot accept {regions}")

        if marker_name is None:
            marker_name = self._default_mark_tag_name

        self._validate_marker_name(marker_name)

        try:
            # FIXME: Also add to Viz. Maybe copy stuff from Footprints here
            if marker_name in self._marker_regions:
                # Should we prune duplicates? Would set() work?
                self._marker_regions[marker_name].extend(regions.regions)
            else:
                self._marker_regions[marker_name] = regions
        except Exception as e:  # pragma: no cover
            self.session.hub.broadcast(SnackbarMessage(
                f"Failed to add markers '{marker_name}': {repr(e)}",
                color="warning", sender=self))
        else:
            self.session.hub.broadcast(MarkersChangedMessage(True, sender=self))

    def remove_markers(self, marker_name=None):
        """Remove some but not all of the markers by name used when
        adding the markers.

        Parameters
        ----------
        marker_name : str
            Name used when the markers were added.
            If not given, will delete markers added under default name.

        """
        raise NotImplementedError  # FIXME

        if marker_name is None:
            marker_name = self._default_mark_tag_name

        try:
            # FIXME: Also remove from Viz
            del self._marker_regions[marker_name]
        except ValueError as e:  # pragma: no cover
            self.session.hub.broadcast(SnackbarMessage(
                f"Failed to remove markers '{marker_name}': {repr(e)}",
                color="warning", sender=self))
        else:
            self.session.hub.broadcast(MarkersChangedMessage(
                len(self._marker_regions) > 0, sender=self))

    def reset_markers(self):
        """Delete all markers."""
        # Grab the entire list of marker names before iterating
        # otherwise what we are iterating over changes.
        for marker_name in self._marker_regions:
            self.remove_markers(marker_name=marker_name)


def _offset_is_pixel_or_sky(x):
    if isinstance(x, u.Quantity):
        if x.unit in (u.dimensionless_unscaled, u.pix):
            coord = 'data'
            val = x.value
        else:
            coord = 'wcs'
            val = x  # Can stay Quantity
    else:
        coord = 'data'
        val = x

    return val, coord
