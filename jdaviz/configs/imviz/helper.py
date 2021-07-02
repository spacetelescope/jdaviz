import os
import re
from copy import deepcopy

from astropy.coordinates import SkyCoord
from astropy.utils.introspection import minversion
from astropy.wcs import NoConvergence
from astropy.wcs.wcsapi import BaseHighLevelWCS
from echo import delay_callback
from glue.core import BaseData, Data

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
            * JWST ASDF-in-FITS file (requires ``jwst``; ``data`` or given
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

        if isinstance(point, SkyCoord):
            i_top = get_top_layer_index(viewer)
            image = viewer.layers[i_top].layer
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

        # Disallow centering outside of display.
        if (pix[0] < viewer.state.x_min or pix[0] > viewer.state.x_max
                or pix[1] < viewer.state.y_min or pix[1] > viewer.state.y_max):  # pragma: no cover
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

    def offset_to(self, dx, dy, skycoord_offset=False):
        """Move the center to a point that is given offset
        away from the current center.

        Parameters
        ----------
        dx, dy : float or `~astropy.units.Quantity`
            Offset value. The presence of unit depends on ``skycoord_offset``.

        skycoord_offset : bool
            If `True`, offset (lon, lat) must be given as ``Quantity``.
            Otherwise, they are in pixel values (float).

        Raises
        ------
        AttributeError
            Sky offset is given but image does not have a valid WCS.

        """
        viewer = self.app.get_viewer("viewer-1")
        width = viewer.state.x_max - viewer.state.x_min
        height = viewer.state.y_max - viewer.state.y_min

        if skycoord_offset:
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
