import os
import re
import sys
import warnings
from copy import deepcopy

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.utils.introspection import minversion
from astropy.wcs import NoConvergence
from astropy.wcs.wcsapi import BaseHighLevelWCS
from echo import delay_callback
from glue.core import BaseData, Data
from glue.core.subset import MaskSubsetState

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.helpers import ConfigHelper

__all__ = ['Imviz']

ASTROPY_LT_4_3 = not minversion('astropy', '4.3')
RESERVED_MARKER_SET_NAMES = ['all']


class Imviz(ConfigHelper):
    """Imviz Helper class"""
    _default_configuration = 'imviz'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Markers
        self._marktags = set()
        self._default_mark_tag_name = 'default-marker-name'
        # marker shape not settable: https://github.com/glue-viz/glue/issues/2202
        self.marker = {'color': 'red', 'alpha': 1.0, 'markersize': 5}

    def load_data(self, data, parser_reference=None, **kwargs):
        """Load data into Imviz.

        Parameters
        ----------
        data : obj or str
            File name or object to be loaded. Supported formats include:

            * ``'filename.fits'`` (or any extension that ``astropy.io.fits``
              supports; first image extension found is loaded unless ``ext``
              keyword is also given)
            * ``'filename.fits[SCI]'`` (loads only first SCI extension)
            * ``'filename.fits[SCI,2]'`` (loads the second SCI extension)
            * ``'filename.jpg'`` (requires ``scikit-image``; grayscale only)
            * ``'filename.png'`` (requires ``scikit-image``; grayscale only)
            * JWST ASDF-in-FITS file (requires ``asdf`` and ``gwcs``; ``data`` or given
              ``ext`` + GWCS)
            * ``astropy.io.fits.HDUList`` object (first image extension found
              is loaded unless ``ext`` keyword is also given)
            * ``astropy.io.fits.ImageHDU`` object
            * ``astropy.nddata.NDData`` object (2D only but may have unit,
              mask, or uncertainty attached)
            * Numpy array (2D only)

        parser_reference
            This is used internally by the app.

        kwargs : dict
            Extra keywords to be passed into app-level parser.
            The only one you might call directly here is ``ext`` (any FITS
            extension format supported by ``astropy.io.fits``) and
            ``show_in_viewer`` (bool).

        Notes
        -----
        When loading image formats that support RGB color like JPG or PNG, the
        files are converted to greyscale. This is done following the algorithm
        of ``skimage.color.rgb2grey``, which involves weighting the channels as
        ``0.2125 R + 0.7154 G + 0.0721 B``. If you prefer a different weighting,
        you can use ``skimage.io.imread`` to produce your own greyscale
        image as Numpy array and load the latter instead.
        """
        if isinstance(data, str):
            filelist = data.split(',')

            if len(filelist) > 1 and 'data_label' in kwargs:
                raise ValueError('Do not manually overwrite data_label for '
                                 'a list of images')

            for data in filelist:
                kw = deepcopy(kwargs)
                filepath, ext, data_label = split_filename_with_fits_ext(data)

                # This, if valid, will overwrite input.
                if ext is not None:
                    kw['ext'] = ext

                # This will only overwrite if not provided.
                if 'data_label' not in kw:
                    kw['data_label'] = data_label

                self.app.load_data(
                    filepath, parser_reference=parser_reference, **kw)

        else:
            self.app.load_data(
                data, parser_reference=parser_reference, **kwargs)

    def save(self, filename):
        """Save out the current image view to given PNG filename."""
        if not filename.lower().endswith('.png'):
            filename = filename + '.png'
        viewer = self.app.get_viewer("viewer-1")
        viewer.figure.save_png(filename=filename)

    def center_on(self, point):
        """Centers the view on a particular point.

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
        viewer = self.app.get_viewer("viewer-1")
        i_top = get_top_layer_index(viewer)
        image = viewer.layers[i_top].layer

        if isinstance(point, SkyCoord):
            if data_has_valid_wcs(image):
                try:
                    pix = image.coords.world_to_pixel(point)  # 0-indexed X, Y
                except NoConvergence as e:  # pragma: no cover
                    self.app.hub.broadcast(SnackbarMessage(
                        f'{point} is likely out of bounds: {repr(e)}',
                        color="warning", sender=self.app))
                    return
            else:
                raise AttributeError(f'{getattr(image, "label", None)} does not have a valid WCS')
        else:
            pix = point

        # Disallow centering outside of display; image.shape is (Y, X)
        eps = sys.float_info.epsilon
        if (not np.all(np.isfinite(pix))
                or pix[0] < -eps or pix[0] >= (image.shape[1] + eps)
                or pix[1] < -eps or pix[1] >= (image.shape[0] + eps)):
            self.app.hub.broadcast(SnackbarMessage(
                f'{pix} is out of bounds', color="warning", sender=self.app))
            return

        with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            width = viewer.state.x_max - viewer.state.x_min
            height = viewer.state.y_max - viewer.state.y_min
            viewer.state.x_min = pix[0] - (width * 0.5)
            viewer.state.y_min = pix[1] - (height * 0.5)
            viewer.state.x_max = viewer.state.x_min + width
            viewer.state.y_max = viewer.state.y_min + height

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
        viewer = self.app.get_viewer("viewer-1")
        width = viewer.state.x_max - viewer.state.x_min
        height = viewer.state.y_max - viewer.state.y_min

        dx, dx_coord = _offset_is_pixel_or_sky(dx)
        dy, dy_coord = _offset_is_pixel_or_sky(dy)

        if dx_coord != dy_coord:
            raise ValueError(f'dx is of type {dx_coord} but dy is of type {dy_coord}')

        if dx_coord == 'wcs':
            i_top = get_top_layer_index(viewer)
            image = viewer.layers[i_top].layer
            if data_has_valid_wcs(image):
                # To avoid distortion headache, assume offset is relative to
                # displayed center.
                x_cen = viewer.state.x_min + (width * 0.5)
                y_cen = viewer.state.y_min + (height * 0.5)
                sky_cen = image.coords.pixel_to_world(x_cen, y_cen)
                if ASTROPY_LT_4_3:
                    from astropy.coordinates import SkyOffsetFrame
                    new_sky_cen = sky_cen.__class__(
                        SkyOffsetFrame(dx, dy, origin=sky_cen.frame).transform_to(sky_cen))
                else:
                    new_sky_cen = sky_cen.spherical_offsets_by(dx, dy)
                self.center_on(new_sky_cen)
            else:
                raise AttributeError(f'{getattr(image, "label", None)} does not have a valid WCS')
        else:
            with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
                viewer.state.x_min += dx
                viewer.state.y_min += dy
                viewer.state.x_max = viewer.state.x_min + width
                viewer.state.y_max = viewer.state.y_min + height

    @property
    def zoom_level(self):
        """Zoom level:

        * 1 means real-pixel-size.
        * 2 means zoomed in by a factor of 2.
        * 0.5 means zoomed out by a factor of 2.
        * 'fit' means zoomed to fit the whole image width into display.

        """
        viewer = self.app.get_viewer("viewer-1")
        if viewer.shape is None:  # pragma: no cover
            raise ValueError('Viewer is still loading, try again later')

        screenx = viewer.shape[1]
        screeny = viewer.shape[0]
        zoom_x = screenx / (viewer.state.x_max - viewer.state.x_min)
        zoom_y = screeny / (viewer.state.y_max - viewer.state.y_min)

        return max(zoom_x, zoom_y)  # Similar to Ginga get_scale()

    # Loosely based on glue/viewers/image/state.py
    @zoom_level.setter
    def zoom_level(self, val):
        if ((not isinstance(val, (int, float)) and val != 'fit') or
                (isinstance(val, (int, float)) and val <= 0)):
            raise ValueError(f'Unsupported zoom level: {val}')

        viewer = self.app.get_viewer("viewer-1")
        image = viewer.state.reference_data
        if (image is None or viewer.shape is None or
                viewer.state.x_att is None or viewer.state.y_att is None):  # pragma: no cover
            return

        # Zoom on X and Y will auto-adjust.
        if val == 'fit':
            # Similar to ImageViewerState.reset_limits() in Glue.
            new_x_min = 0
            new_x_max = image.shape[viewer.state.x_att.axis]
        else:
            cur_xcen = (viewer.state.x_min + viewer.state.x_max) * 0.5
            new_dx = viewer.shape[1] * 0.5 / val
            new_x_min = cur_xcen - new_dx
            new_x_max = cur_xcen + new_dx

        with delay_callback(viewer.state, 'x_min', 'x_max'):
            viewer.state.x_min = new_x_min - 0.5
            viewer.state.x_max = new_x_max - 0.5

        # We need to adjust the limits in here to avoid triggering all
        # the update events then changing the limits again.
        viewer.state._adjust_limits_aspect()

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
    def marker(self):
        """Marker to use.

        Marker can be set as follows; e.g.::

            {'color': 'red', 'alpha': 1.0, 'markersize': 3}
            {'color': '#ff0000', 'alpha': 0.5, 'markersize': 10}
            {'color': (1, 0, 0)}

        The valid properties for markers in imviz are listed at
        https://docs.glueviz.org/en/stable/api/glue.core.visual.VisualAttributes.html

        """
        return self._marker_dict

    @marker.setter
    def marker(self, val):
        # Validation: Ideally Glue should do this but we have to due to
        # https://github.com/glue-viz/glue/issues/2203
        given = set(val.keys())
        allowed = set(('color', 'alpha', 'markersize'))
        if not given.issubset(allowed):
            raise KeyError(f'Invalid attribute(s): {given - allowed}')
        if 'color' in val:
            from matplotlib.colors import ColorConverter
            ColorConverter().to_rgb(val['color'])  # ValueError: Invalid RGBA argument
        if 'alpha' in val:
            alpha = val['alpha']
            if not isinstance(alpha, (int, float)) or alpha < 0 or alpha > 1:
                raise ValueError(f'Invalid alpha: {alpha}')
        if 'markersize' in val:
            size = val['markersize']
            if not isinstance(size, (int, float)):
                raise ValueError(f'Invalid marker size: {size}')

        # Only set this once we have successfully validated a marker.
        # Those not set here use Glue defaults.
        self._marker_dict = val

    def _validate_marker_name(self, marker_name):
        """Raise an error if the marker_name is not allowed."""
        if marker_name in RESERVED_MARKER_SET_NAMES:
            raise ValueError(
                f"The marker name {marker_name} is not allowed. Any name is "
                f"allowed except these: {', '.join(RESERVED_MARKER_SET_NAMES)}")

    def add_markers(self, table, x_colname='x', y_colname='y',
                    skycoord_colname='coord', use_skycoord=False,
                    marker_name=None):
        """Creates markers w.r.t. the reference image at given points
        in the table.

        .. note:: Use `marker` to change marker appearance.

        Parameters
        ----------
        table : `~astropy.table.Table`
            Table containing marker locations.

        x_colname, y_colname : str
            Column names for X and Y.
            Coordinates must be 0-indexed.

        skycoord_colname : str
            Column name with `~astropy.coordinates.SkyCoord` objects.

        use_skycoord : bool
            If `True`, use ``skycoord_colname`` to mark.
            Otherwise, use ``x_colname`` and ``y_colname``.

        marker_name : str, optional
            Name to assign the markers in the table. Providing a name
            allows markers to be removed by name at a later time.

        Raises
        ------
        AttributeError
            Sky coordinates are given but reference image does not have a valid WCS.

        ValueError
            Invalid marker name.

        """
        if marker_name is None:
            marker_name = self._default_mark_tag_name

        self._validate_marker_name(marker_name)
        viewer = self.app.get_viewer("viewer-1")
        jglue = self.app.session.application

        # TODO: How to link to invidual images separately for X/Y? add_link in loop does not work.
        # Link markers to reference image data.
        image = viewer.state.reference_data

        # TODO: Is Glue smart enough to no-op if link already there?
        if use_skycoord:
            if not data_has_valid_wcs(image):
                raise AttributeError(f'{getattr(image, "label", None)} does not have a valid WCS')
            sky = table[skycoord_colname]
            t_glue = Data(marker_name, ra=sky.ra.deg, dec=sky.dec.deg)
            jglue.data_collection[marker_name] = t_glue
            jglue.add_link(t_glue, 'ra', image, 'Right Ascension')
            jglue.add_link(t_glue, 'dec', image, 'Declination')
        else:
            t_glue = Data(marker_name, **table[x_colname, y_colname])
            jglue.data_collection[marker_name] = t_glue
            jglue.add_link(t_glue, x_colname, image, image.pixel_component_ids[1].label)
            jglue.add_link(t_glue, y_colname, image, image.pixel_component_ids[0].label)

        try:
            viewer.add_data(t_glue)
        except Exception as e:  # pragma: no cover
            self.app.hub.broadcast(SnackbarMessage(
                f"Failed to add markers '{marker_name}': {repr(e)}",
                color="warning", sender=self.app))
        else:
            # Only can set alpha and color using viewer.add_data(), so brute force here instead.
            # https://github.com/glue-viz/glue/issues/2201
            for key, val in self.marker.items():
                setattr(self.app.data_collection[self.app.data_collection.labels.index(marker_name)].style, key, val)  # noqa

            self._marktags.add(marker_name)

    def remove_markers(self, marker_name=None):
        """Remove some but not all of the markers by name used when
        adding the markers.

        Parameters
        ----------
        marker_name : str
            Name used when the markers were added.
            If not given, will delete markers added under default name.

        """
        if marker_name is None:
            marker_name = self._default_mark_tag_name

        try:
            i = self.app.data_collection.labels.index(marker_name)
        except ValueError as e:  # pragma: no cover
            self.app.hub.broadcast(SnackbarMessage(
                f"Failed to remove markers '{marker_name}': {repr(e)}",
                color="warning", sender=self.app))
            return

        data = self.app.data_collection[i]
        self.app.data_collection.remove(data)
        self._marktags.remove(marker_name)

    def reset_markers(self):
        """Delete all markers."""
        # Grab the entire list of marker names before iterating
        # otherwise what we are iterating over changes.
        for marker_name in list(self._marktags):
            self.remove_markers(marker_name=marker_name)

    def load_static_regions(self, regions, **kwargs):
        """Load given region(s) into the viewer.
        Region(s) is relative to the reference image.
        Once loaded, the region(s) cannot be modified.

        Parameters
        ----------
        regions : dict
            Dictionary mapping desired region name to one of the following:

            * Astropy ``regions`` object
            * ``photutils`` apertures (limited support until ``photutils``
              fully supports ``regions``)
            * Numpy boolean array (shape must match data)

            Region name that starts with "Subset" is forbidden and reserved
            for internal use only.

        kwargs : dict
            Extra keywords to be passed into the region's ``to_mask`` method.
            This is ignored if Numpy array is given.

        """
        viewer = self.app.get_viewer("viewer-1")
        data = viewer.state.reference_data

        for subset_label, region in regions.items():
            if subset_label.startswith('Subset'):
                warnings.warn(f'{subset_label} is not allowed, skipping. '
                              'Do not use region name that starts with Subset.')
                continue

            if hasattr(region, 'to_pixel'):
                if data_has_valid_wcs(data):
                    pixreg = region.to_pixel(data.coords)
                    mask = pixreg.to_mask(**kwargs)
                    im = mask.to_image(data.shape)
                else:
                    warnings.warn(f'{region} given but data has no valid WCS, skipping')
                    continue
            elif hasattr(region, 'to_mask'):
                mask = region.to_mask(**kwargs)
                im = mask.to_image(data.shape)
            elif (isinstance(region, np.ndarray) and region.shape == data.shape
                    and region.dtype == np.bool_):
                im = region
            else:
                warnings.warn(f'Unsupported region type: {type(region)}, skipping')
                continue

            # NOTE: Region creation info is thus lost.
            state = MaskSubsetState(im, data.pixel_component_ids)
            self.app.data_collection.new_subset_group(subset_label, state)

    def get_interactive_regions(self):
        """Return regions interactively drawn in the viewer.
        This does not return regions added via :meth:`load_static_regions`.

        Returns
        -------
        regions : dict
            Dictionary mapping interactive region names to respective Astropy
            ``regions`` objects.

        """
        return self.app.get_subsets_from_viewer('viewer-1')


def split_filename_with_fits_ext(filename):
    """Split a ``filename[ext]`` input into filename and FITS extension.

    Parameters
    ----------
    filename : str
        Can be a plain filename or ``filename[ext]``. The latter is a form
        of input that is commonly used by DS9. Example values:

        * ``'myimage.fits'``
        * ``'myimage.fits[SCI]'`` (assumes ``EXTVER=1``)
        * ``'myimage.fits[SCI,1]'``

    Returns
    -------
    filepath : str
        Path to the file, without extension.

    ext : str, tuple, or `None`
        FITS extension, if given. Examples: ``'SCI'`` or ``('SCI', 1)``

    data_label : str
        Human-readable data label for Glue. Extension info will be added
        later in the parser.

    """
    s = os.path.splitext(filename)
    ext_match = re.match(r'(.+)\[(.+)\]', s[1])
    if ext_match is None:
        sfx = s[1]
        ext = None
    else:
        sfx = ext_match.group(1)
        ext = ext_match.group(2)
        if ',' in ext:
            ext = ext.split(',')
            ext[1] = int(ext[1])
            ext = tuple(ext)
        elif not re.match(r'\D+', ext):
            ext = int(ext)

    filepath = f'{s[0]}{sfx}'
    data_label = os.path.basename(s[0])

    return filepath, ext, data_label


def data_has_valid_wcs(data):
    return hasattr(data, 'coords') and isinstance(data.coords, BaseHighLevelWCS)


def layer_is_image_data(layer):
    return isinstance(layer, BaseData) and layer.ndim == 2


def get_top_layer_index(viewer):
    """Get index of the top visible image layer in Imviz.
    This is because when blinked, first layer might not be top visible layer.

    """
    return [i for i, lyr in enumerate(viewer.layers)
            if lyr.visible and layer_is_image_data(lyr.layer)][-1]


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
